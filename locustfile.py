import itertools
import random
import time
import uuid

from locust import HttpUser, between, task


_user_counter = itertools.count(1)


class AuthenticatedUser(HttpUser):
    """
    Simulates a normal signed-in user using the routes currently mounted by the app.
    """

    wait_time = between(1, 3)
    token = None
    user_id = None
    email = None
    password = None
    name = None

    def on_start(self):
        user_number = next(_user_counter)
        run_suffix = f"{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"
        self.name = f"Locust User {user_number}"
        self.email = f"locust-{user_number}-{run_suffix}@example.com"
        self.password = "locustpass123"

        with self.client.post(
            "/api/v1/users",
            json={
                "name": self.name,
                "email": self.email,
                "password": self.password,
            },
            name="/api/v1/users [create]",
            catch_response=True,
        ) as response:
            if response.status_code not in (200, 201):
                response.failure(f"unexpected status during signup: {response.status_code}")
                return
            self.user_id = response.json()["id"]
            response.success()

        self.login()

    def login(self):
        with self.client.post(
            "/api/v1/auth/login",
            json={"email": self.email, "password": self.password},
            name="/api/v1/auth/login [success]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                self.token = response.json()["access_token"]
                response.success()
                return True

            self.token = None
            if response.status_code == 429:
                response.failure("login rate-limited during authenticated flow")
            else:
                response.failure(f"unexpected login status: {response.status_code}")
            return False

    def auth_headers(self):
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}

    def ensure_authenticated(self):
        if self.token:
            return True
        return self.login()

    @task(4)
    def get_me(self):
        if not self.token:
            return
        self.client.get("/api/v1/auth/me", headers=self.auth_headers())

    @task(3)
    def get_own_user(self):
        if not self.token:
            return
        if self.user_id is not None:
            self.client.get(
                f"/api/v1/users/{self.user_id}",
                headers=self.auth_headers(),
                name="/api/v1/users/:id [get self]",
            )

    @task(2)
    def update_own_user(self):
        if not self.token:
            return
        if self.user_id is not None:
            self.client.patch(
                f"/api/v1/users/{self.user_id}",
                json={"name": f"{self.name} {random.randint(1, 9999)}"},
                headers=self.auth_headers(),
                name="/api/v1/users/:id [patch self]",
            )

    @task(1)
    def refresh_token(self):
        if not self.token:
            return
        self.client.post("/api/v1/auth/refresh", name="/api/v1/auth/refresh")

    @task(1)
    def health_check(self):
        self.client.get("/health")


class AnonymousUser(HttpUser):
    """
    Simulates unauthenticated traffic against public routes.
    """

    wait_time = between(2, 5)

    @task(3)
    def try_login_wrong_password(self):
        with self.client.post(
            "/api/v1/auth/login",
            json={
                "email": "nobody@test.com",
                "password": "wrongpassword",
            },
            name="/api/v1/auth/login [invalid]",
            catch_response=True,
        ) as response:
            if response.status_code in (401, 429):
                response.success()
            else:
                response.failure(
                    f"unexpected invalid-login status: {response.status_code}"
                )

    @task(1)
    def health_check(self):
        self.client.get("/health")
