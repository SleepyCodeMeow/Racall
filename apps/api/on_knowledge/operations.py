from functools import wraps


def notebook_operation(method):
    @wraps(method)
    def guarded(self, notebook, *args, **kwargs):
        with self.store.notebook_operation(notebook):
            return method(self, notebook, *args, **kwargs)

    return guarded
