import os
import re

from renderg_api.constants import JobStatus

try:
    import _winreg
    winreg = _winreg
except ImportError:
    import winreg

from renderg_utils.exception import DCCFileNotExistsError
from renderg_utils.exception import DCCExeNotFoundError
from renderg_utils.exception import AnalyzeFailError
from renderg_utils.exception import ErrorCode, WarnCode

import renderg_utils


class AnalyzeHoudini(object):
    def __init__(self,
                 dcc_file,
                 dcc_version,
                 workspace=None,
                 dcc_exe_path=None,
                 api=None,
                 project_id=None,
                 env_id=None,
                 job_id=None
                 ):

        if not os.path.isfile(dcc_file):
            raise DCCFileNotExistsError(ErrorCode.DCCFileNotExistsError, dcc_file)

        self.dcc_file = dcc_file
        self.dcc_version = dcc_version
        self.dcc_exe_path = dcc_exe_path
        self.api = api
        self.project_id = project_id
        self.env_id = env_id
        self.job_id = job_id

        if not job_id:
            self.job_id = self.api.job.new_job(self.dcc_file, self.project_id, self.env_id)

        self.workspace = os.path.join(renderg_utils.get_workspace(workspace), str(self.job_id))
        if not os.path.isdir(self.workspace):
            os.makedirs(self.workspace)

        self.info_path = os.path.join(self.workspace, "info.cfg")
        self.warning_path = os.path.join(self.workspace, "warning.json")

        self.warning_info = {}

    def add_warning(self, warn, *args):
        self.warning_info.update({warn.code(): warn.msg(*args)})
        renderg_utils.write_json(self.warning_path, self.warning_info)

    def check_file_version(self):
        regex = re.compile(r"set -g _HIP_SAVEVERSION = '(?P<version>.*?)'\s")
        version = renderg_utils.get_dcc_file_version(self.dcc_file, regex)
        if version != self.dcc_version:
            self.add_warning(WarnCode.DCCVersionNotMatchWarn, version, self.dcc_version)

    def find_dcc_exe(self):
        dcc_exe_path = ''
        local_dcc_exe_path = r"C:\Program Files\Side Effects Software\Houdini {}\bin\hython.exe".format(self.dcc_version)

        if os.path.isfile(local_dcc_exe_path):
            dcc_exe_path = local_dcc_exe_path
        else:

            try:
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Side Effects Software\Houdini ' + self.dcc_version
                )
                regedit_dcc_exe_path, _ = winreg.QueryValueEx(key, "InstallPath")
                dcc_exe_path = os.path.join(regedit_dcc_exe_path, r'bin\hython.exe')
            except BaseException as err:
                print(err.__str__())
        if not dcc_exe_path or not os.path.isfile(dcc_exe_path):
            raise DCCExeNotFoundError(ErrorCode.DCCExeNotFoundError, dcc_exe_path)

        return dcc_exe_path

    def analyze(self):
        self.check_file_version()
        if not self.dcc_exe_path:
            self.dcc_exe_path = self.find_dcc_exe()

        self._update_analyze_status(JobStatus.STATUS_ANALYZE_DOING)
        script_path = os.path.join(os.path.dirname(__file__), "houdini/run.py")
        cmd = '"{exe_path}" "{script_path}" -input "{dcc_file}" -output "{info_file}"'.format(
            exe_path=self.dcc_exe_path,
            script_path=script_path,
            dcc_file=self.dcc_file,
            info_file=self.info_path
        )
        print(cmd)
        code = renderg_utils.run_cmd(cmd, shell=True)
        if code != 0:
            self._update_analyze_status(JobStatus.STATUS_ANALYZE_FAILED)
            raise AnalyzeFailError(ErrorCode.AnalyzeFailError, "analyze exits unexpectedly")

        if not os.path.isfile(self.info_path):
            self._update_analyze_status(JobStatus.STATUS_ANALYZE_FAILED)
            raise AnalyzeFailError(ErrorCode.AnalyzeFailError, "info.cfg not found.")

        self._update_analyze_status(JobStatus.STATUS_ANALYZED)
        return self

    def _update_analyze_status(self, status):
        self.api.job.update_job_status(self.job_id, status)
