### 准备

1. 创建虚拟环境

   ```shell
   python -m venv venv
   ```

2. 安装 renderg-sdk

   ```shell
   pip install git+https://github.com/renderg-repo/renderg-sdk.git
   ```

3. 创建配置文件 `config.json`

   ```shell
   {
     "AUTH_KEY": "*******************",
     "CLUSTER_ID": 27,
     "PROJECT_ID": 21479,
     "ENV_ID": 7715,
     "ZONE_ID": 1003,
     "RAM_LIMIT": "64G"
   }
   ```

- AUTH_KEY 用户身份认证，请联系 [RenderG 渲染农场](https://www.renderg.com/)平台技术支持获取；
- CLUSTER_ID 区域 ID ，一般为固定；
- PROJECT_ID，提交任务默认项目，在客户端项目管理中创建；
- ENV_ID ，提交任务默认环境，在客户端环境管理中创建；
- ZONE_ID，提交任务默认配置，默认请使用 1003；
- RAM_LIMIT，提交任务默认内存配置，64G、128G、256G 可选；

### 分析资产并上传

```python
from renderg_utils import utils
from analyze_houdini import AnalyzeHoudini
from renderg_api import RenderGAPI
from renderg_api.constants import TransferLines
from renderg_api.param_check import RenderGParamChecker
from renderg_upload.rgUpload import RendergUpload
# ========分析资产和渲染参数==========
# 1. 读取配置文件
config = utils.read_json("./config.json")

api = RenderGAPI(auth_key=config["AUTH_KEY"], cluster_id=config["CLUSTER_ID"])

# 2.  创建任务信息
analyze_info = {
    "dcc_file": r"D:\houdini_file\JSBL_lgt_qunji_wmy_v001.hip",
    "dcc_version": "19.0.622",
    "workspace": r"D:\workspace",  # 工作目录，存放日志、分析结果等文件。默认为 %USERPROFILE%\RenderG_WorkSpace
    "api": api,
    "project_id": config["PROJECT_ID"],  # 项目ID
    "env_id": config["ENV_ID"],  # 环境ID
    "job_id": None,  # 任务号为空时，自动创建任务号
}
# 3. 分析资产列表和场景渲染参数
analyze_obj = AnalyzeHoudini(**analyze_info)
analyze_obj.analyze()
print(analyze_obj.info_path)

# 4. 设置选择参数信息
param_check_obj = RenderGParamChecker(api, analyze_obj)
render_params = {
    "ChunkSize": 1,  # 一机多帧
    "Mark": "",  # 任务备注信息
    "PriorityFrames": "010:",  # 优先渲染帧 例：101:100-108x2 代表渲染首尾帧和100-108步长为2的帧

    "zone_id": config["ZONE_ID"],  # CPU 配置信息
    "ram_limit": config["RAM_LIMIT"],  # 内存配置
}
param_check_obj.execute(**render_params)

# ========上传任务并提交==========
# 1. 获取 info.cfg 和 任务 ID 信息
info_path = analyze_obj.info_path
job_id = analyze_obj.job_id

# 2. 配置上传任务信息 
upload_kwargs = {
    "api": api,
    "job_id": job_id,
    "info_path": info_path,
    "line": TransferLines.LINE_RENDERG,
    "spend": 200 # 上传速度限制，单位为 Mbps
}
# 3. 开始上传
renderg_upload = RendergUpload(**upload_kwargs)
renderg_upload.upload()

# 4. 上传完成，提交任务，开始渲染
submit = api.job.submit_job(job_id)
print(submit["msg"])

```



