from .client import TraccarResponseError, traccar_get_collection


def listar_dispositivos():
    dispositivos = traccar_get_collection('/api/devices', ('id', 'name'))
    for dispositivo in dispositivos:
        identificador = dispositivo['id']
        if type(identificador) is not int or identificador <= 0:
            raise TraccarResponseError('Traccar retornou ID de dispositivo inválido.')
    return dispositivos
