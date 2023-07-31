from typing import List

import pytest
import responses

from darwin.future.core.client import CoreClient
from darwin.future.data_objects.workflow import WFType, WorkflowModel
from darwin.future.meta.objects.stage import Stage
from darwin.future.meta.objects.workflow import Workflow
from darwin.future.meta.queries.stage import StageQuery
from darwin.future.tests.core.fixtures import *


@pytest.fixture
def filled_query(base_client: CoreClient, base_workflow_meta: Workflow) -> StageQuery:
    return StageQuery(base_client, meta_params={"workflow_id": str(base_workflow_meta.id)})


@pytest.fixture
def base_workflow_meta(base_client: CoreClient, base_single_workflow_object: dict) -> Workflow:
    return Workflow(base_client, WorkflowModel.parse_obj(base_single_workflow_object))


@pytest.fixture
def multi_stage_workflow_object(base_single_workflow_object: dict) -> dict:
    stage = base_single_workflow_object["stages"][0]
    types = [t for t in WFType.__members__.values()] * 3
    stages = []
    for i, t in enumerate(types):
        temp = stage.copy()
        temp["name"] = f"stage{i}"
        temp["type"] = t.value
        stages.append(temp)
    base_single_workflow_object["stages"] = stages
    return base_single_workflow_object


def test_stage_collects_basic(
    filled_query: StageQuery, base_single_workflow_object: dict, base_workflow_meta: Workflow
) -> None:
    UUID = base_workflow_meta.id
    with responses.RequestsMock() as rsps:
        endpoint = filled_query.client.config.api_endpoint + f"v2/teams/default-team/workflows/{UUID}"
        rsps.add(responses.GET, endpoint, json=base_single_workflow_object)
        stages = filled_query.collect()
        assert len(stages) == len(base_workflow_meta.stages)
        assert isinstance(stages[0], Stage)


def test_stage_filters_basic(
    filled_query: StageQuery, multi_stage_workflow_object: dict, base_workflow_meta: Workflow
) -> None:
    UUID = base_workflow_meta.id
    with responses.RequestsMock() as rsps:
        endpoint = filled_query.client.config.api_endpoint + f"v2/teams/default-team/workflows/{UUID}"
        rsps.add(responses.GET, endpoint, json=multi_stage_workflow_object)
        stages = filled_query.where({"name": "name", "param": "stage1"}).collect()
        assert len(stages) == 1
        assert isinstance(stages[0], Stage)
        assert stages[0]._item is not None
        assert stages[0]._item.name == "stage1"


@pytest.mark.parametrize("wf_type", [t for t in WFType.__members__.values()])
def test_stage_filters_WFType(
    wf_type: WFType, filled_query: StageQuery, multi_stage_workflow_object: dict, base_workflow_meta: Workflow
) -> None:
    UUID = base_workflow_meta.id
    with responses.RequestsMock() as rsps:
        endpoint = filled_query.client.config.api_endpoint + f"v2/teams/default-team/workflows/{UUID}"
        rsps.add(responses.GET, endpoint, json=multi_stage_workflow_object)
        stages = filled_query.where({"name": "type", "param": wf_type.value}).collect()
        assert len(stages) == 3
        assert isinstance(stages[0], Stage)
        for stage in stages:
            assert stage._item is not None
            assert stage._item.type == wf_type
