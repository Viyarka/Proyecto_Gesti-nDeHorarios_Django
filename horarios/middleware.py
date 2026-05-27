class AuditSessionMiddleware:
    """Guarda el usuario actual en request para usarlo en vistas y logs.

    Es un middleware muy pequeño: pasa la petición a la vista y no altera la respuesta.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)
