import json
import os
import time

from renderg_api.constants import JobStatus
import renderg_utils
from renderg_transfer.TransferHelper import TransferHelper
from renderg_transfer.MQClient import MqttClient


class RenderGDownload:

    def __init__(self, api, job_id, download_path, line, cluster_id, speed=1000, workspace=None):
        self.api = api
        if job_id is not None:
            self.transfer_config = api.transfer.get_transfer_config(job_id)
            self.user_id = self.transfer_config.get('username').split('_')[2]
        else:
            self.transfer_config = api.transfer.get_transfer_cluster(cluster_id)[0]
            self.user_id = self.transfer_config.get('username').split('_')[2]

        self.host, self.port = api.transfer.get_transfer_line(line)
        self.download_path = download_path
        self.job_id = job_id
        self.speed = speed

        self.workspace = renderg_utils.get_workspace(workspace)
        if not os.path.isdir(self.workspace):
            os.makedirs(self.workspace)

        self.log_path = os.path.join(self.workspace, 'log')
        if not os.path.isdir(self.log_path):
            os.makedirs(self.log_path)

        auth_key = self.api.mqConnect.get_key()
        self.mqtt_client = MqttClient('{}_sdk'.format(self.user_id), auth_key)
        self.jobEnd_list = []

    def mq_callback(self, result):
        print("Received message: " + result)
        payload = json.loads(result)
        if payload.get('type_id') == '030003':
            data = payload.get('data')
            job_id = data.get('job_id')
            self.jobEnd_list.append(str(job_id))

    def auto_download_after_job_completed(self):
        job_info = self.api.job.get_jobs_info(self.job_id)
        status = job_info.get('Status')
        if status != JobStatus.STATUS_COMPLETED:
            # 任务未完成，监听mqtt状态，等待完成
            self.mqtt_client.subscribe(
                'mqtt/front/user/{user_id}/{job_id}'.format(user_id=self.user_id, job_id=self.job_id),
                self.mq_callback
            )
            while True:
                print("监听任务 {job_id}".format(job_id=self.job_id))
                if str(self.job_id) in self.jobEnd_list:
                    print("{job_id}:渲染完成".format(job_id=self.job_id))
                    self.mqtt_client.unsubscribe(
                        'mqtt/front/user/{user_id}/{job_id}'.format(user_id=self.user_id, job_id=self.job_id)
                    )
                    break
                time.sleep(3)

        username = self.transfer_config.get("output_username")
        password = self.transfer_config.get("password")

        # 下载：
        cmd_pass = "set ASPERA_SCP_PASS={password}".format(password=password)
        files_source_path = './{job_id}/'.format(job_id=self.job_id)
        files_dest_path = self.download_path
        cmd = TransferHelper.create_ascp_command(
            cmd_pass=cmd_pass,
            mode="recv",
            host=self.host,
            port=self.port,
            username=username,
            max_speed=self.speed,
            log_dir=self.log_path,
            source_path=files_source_path,
            dest_path=files_dest_path
        )
        print(cmd)
        code = renderg_utils.run_cmd(cmd, shell=True)
        print("cmd return code: {}".format(code))
        return "success"

    def custom_download(self, server_path):
        username = self.transfer_config.get("output_username")
        password = self.transfer_config.get("password")

        source_paths = []
        dest_paths = []
        for source in server_path:
            source_paths.append(source)
            dest_paths.append("{}/{}".format(self.download_path, source))

        file_pair_list_path = TransferHelper.create_file_pair_list_file(
            self.workspace, self.job_id, source_paths, dest_paths
        )

        # 下载：
        cmd_pass = "set ASPERA_SCP_PASS={password}".format(password=password)

        cmd = TransferHelper.create_ascp_command(
            cmd_pass=cmd_pass,
            mode="recv",
            host=self.host,
            port=self.port,
            username=username,
            max_speed=self.speed,
            log_dir=self.log_path,
            pair_list_file=file_pair_list_path
        )
        print(cmd)
        code = renderg_utils.run_cmd(cmd, shell=True)
        print("cmd return code: {}".format(code))
