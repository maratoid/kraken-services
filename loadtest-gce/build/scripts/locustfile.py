from locust import HttpLocust, TaskSet, task

class FooBar(TaskSet):
    @task(1)
    def index(self):
        self.client.get("/foo/")

    @task(2)
    def profile(self):
        self.client.get("/bar/")

class WebsiteUser(HttpLocust):
    task_set = FooBar