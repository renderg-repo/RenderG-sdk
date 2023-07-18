from enum import Enum


def assemble_api_url(domain, operators, protocol='https'):
    """Assemble the requests api url."""
    if isinstance(operators, Enum):
        operators = operators.value
    return '{}://{}{}'.format(protocol, domain, operators)


class ApiUrl(str, Enum):
    NewJob = "/api/v1/front/job/add"
    UpdateJobStatus = "/api/v1/front/job/status"
    ControlJob = "/api/v1/front/job/control"
    SubmitJob = "/api/v1/front/job/submit"
    DelJob = "/api/v1/front/job/del"
    SetJobConfig = "/api/v1/front/job/cluster_id"

    GetClusterList = "/api/v1/front/cluster/current"
    GetZoneList = "/api/v1/front/zone/list"

    GetEnvList = "/api/v1/front/environment/list"
    GetProjectList = "/api/v2/front/project/all"

    GetTransferLine = "/api/v1/front/transfer/lines"
    GetTransferConfig = "/api/v1/front/job/transfer_plus"
