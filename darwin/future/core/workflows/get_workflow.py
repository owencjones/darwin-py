from typing import List, Optional, Tuple

from pydantic import parse_obj_as

from darwin.future.core.client import CoreClient
from darwin.future.data_objects.workflow import WorkflowModel


def get_workflow(
    client: CoreClient, workflow_id: str, team_slug: Optional[str] = None
) -> Tuple[Optional[WorkflowModel], List[Exception]]:
    workflow: Optional[WorkflowModel] = None
    exceptions: List[Exception] = []

    try:
        team_slug = team_slug or client.config.default_team
        response = client.get(f"/v2/teams/{team_slug}/workflows/{workflow_id}")

        workflow = parse_obj_as(WorkflowModel, response)
    except Exception as e:
        exceptions.append(e)

    return workflow, exceptions
