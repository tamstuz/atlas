from ..schemas.task_packet import TaskPacket


def create_initial_task(project_id: str, request: str) -> TaskPacket:
    return TaskPacket(project_id=project_id, request=request)
