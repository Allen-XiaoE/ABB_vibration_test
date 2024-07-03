from requests import Session
from requests.auth import HTTPBasicAuth
import json
import warnings
 
warnings.filterwarnings("ignore")

class RWS:

    def __init__(
        self,
        protocol="https://",
        url="localhost:80",
        username="Default User",
        password="robotics",
    ):
        self.baseurl = protocol + url
        self.session = Session()
        self.session.auth = HTTPBasicAuth(username=username, password=password)
        self.session.headers = {
            "Accept": "application/hal+json;v=2.0",
            "Content-Type": "application/x-www-form-urlencoded;v=2.0",
        }

    # region Basic Method
    def get(self, rw):
        try:
            url = self.baseurl + rw
            response = self.session.get(url=url, verify=False)
            return response
        except Exception as e:
            raise RuntimeError(repr(e))

    def post(self, rw, data=None):
        try:
            url = self.baseurl + rw
            response = self.session.post(url=url, verify=False, data=data)
            return response
        except Exception as e:
            raise RuntimeError(repr(e))

    def put(self, rw, data=None):
        try:
            self.session.headers["Content-Type"] = "text/plain;v=2.0"
            url = self.baseurl + rw
            response = self.session.put(url=url, verify=False, data=data)
            self.session.headers["Content-Type"] = (
                "application/x-www-form-urlencoded;v=2.0"
            )
            return response
        except Exception as e:
            self.session.headers["Content-Type"] = (
                "application/x-www-form-urlencoded;v=2.0"
            )
            raise RuntimeError(repr(e))

    def delete(self, rw, data=None):
        try:
            url = self.baseurl + rw
            response = self.session.delete(url=url, verify=False, data=data)
            return response
        except Exception as e:
            raise RuntimeError(repr(e))

    def output(self, response):
        if response.status_code in [200, 201, 202, 204]:
            return "OK"
        else:
            return (
                f"Error Code: {response.status_code}, Error Reason: {response.reason}, Error Conetent: {response.text}"
            )
    # endregion

    # region Get Info
    def connect_verification(self):
        try:
            response = self.get(rw="/")
            return self.output(response)
        except Exception as e:
            return repr(e)

    def GETserial(self):
        try:
            response = self.get(rw="/ctrl/identity")
            if response.status_code == 200:
                json_data = json.loads(response.text)
                info = json_data["state"][0]["ctrl-id"]
                return info
            else:
                print(
                    f"Error Code: {response.status_code}, Error Reason: {response.reason}"
                )
        except Exception as e:
            return repr(e)

    def GETopmode(self):
        try:
            response = self.get(rw="/rw/panel/opmode")
            if response.status_code == 200:
                json_data = json.loads(response.text)
                opmode = json_data["state"][0]["opmode"]
                return opmode
            else:
                print(
                    f"Error Code: {response.status_code}, Error Reason: {response.reason}"
                )
        except Exception as e:
            return repr(e)

    def GETmotormode(self):
        try:
            response = self.get(rw="/rw/panel/ctrl-state")
            if response.status_code == 200:
                json_data = json.loads(response.text)
                motormode = json_data["state"][0]["ctrlstate"]
                return motormode
            else:
                print(
                    f"Error Code: {response.status_code}, Error Reason: {response.reason}"
                )
        except Exception as e:
            return repr(e)

    def GETrapidstatus(self):
        try:
            response = self.get(rw="/rw/rapid/execution")
            if response.status_code == 200:
                json_data = json.loads(response.text)
                rapidstatus = json_data["state"][0]["ctrlexecstate"]
                return rapidstatus
            else:
                print(
                    f"Error Code: {response.status_code}, Error Reason: {response.reason}"
                )
        except Exception as e:
            return repr(e)
    # endregion

    # region File operation
    def uploadfile(self, path, content):
        try:
            response = self.put(rw=f"/fileservice/{path}", data=content)
            return self.output(response)
        except Exception as e:
            return repr(e)

    def deletefile(self, path):
        try:
            response = self.delete(rw=f"/fileservice/{path}")
            return self.output(response)
        except Exception as e:
            return repr(e)
    # endregion
    
    def mastership(self, cmd="RQ"):
        try:
            if cmd == "RQ":
                RQE = "request"
            elif cmd == "RE":
                RQE = "release"
            elif cmd == "RMQ":
                RQE = "edit/request"
            elif cmd == "RME":
                RQE = "edit/release"
            else:
                return f"cmd = {cmd}不存在,请使用正确的cmd!正确的为:RQ--requeset, RE--release, RMQ--motion/request, RME--motion/release!"
            response = self.post(rw=f"/rw/mastership/{RQE}")
            return self.output(response)
        except Exception as e:
            return repr(e)

    def motor(self, cmd):
        data = {"ctrl-state": cmd}
        try:
            response = self.post(rw="/rw/panel/ctrl-state", data=data)
            return self.output(response)
        except Exception as e:
            return repr(e)

    # def restart(self):
    #     data = {"ctrl-state": cmd}
    #     try:
    #         response = self.post(rw="/rw/panel/ctrl-state", data=data)
    #         return self.output(response)
    #     except Exception as e:
    #         return repr(e)
    # region Rapid operation
    def loadmodule(self, path):
        data = {"modulepath": path, "replace": "true"}
        try:
            self.mastership(cmd="RQ")
            response = self.post(rw="/rw/rapid/tasks/T_ROB1/loadmod", data=data)
            self.mastership(cmd="RE")
            return self.output(response)
        except Exception as e:
            self.mastership(cmd="RE")
            return repr(e)

    def unloadmodule(self, module):
        data = {"module": module}
        try:
            self.mastership(cmd="RQ")
            response = self.post(rw="/rw/rapid/tasks/T_ROB1/unloadmod", data=data)
            self.mastership(cmd="RE")
            return self.output(response)
        except Exception as e:
            self.mastership(cmd="RE")
            return repr(e)

    def excuseRapid(self):
        data = {
            "regain": "continue",
            "execmode": "continue",
            "cycle": "once",
            "condition": "none",
            "stopatbp": "disabled",
            "alltaskbytsp": "false",
        }
        try:
            self.mastership(cmd="RMQ")
            response = self.post(rw="/rw/rapid/execution/start", data=data)
            self.mastership(cmd="RME")
            return self.output(response)
        except Exception as e:
            self.mastership(cmd="RME")
            return repr(e)

    def stopexcuseRapid(self):
        data = {"stopmode": "stop", "usetsp": "normal "}
        try:
            self.mastership(cmd="RQ")
            response = self.post(rw="/rw/rapid/execution/stop", data=data)
            self.mastership(cmd="RE")
            return self.output(response)
        except Exception as e:
            self.mastership(cmd="RE")
            return repr(e)

    def pptoRoutine(self, routine, module, task="T_ROB1"):
        data = {"routine": routine, "module": module}
        try:
            self.mastership(cmd="RQ")
            response = self.post(rw=f"/rw/rapid/tasks/{task}/pcp/routine", data=data)
            self.mastership(cmd="RE")
            return self.output(response)
        except Exception as e:
            self.mastership(cmd="RE")
            return repr(e)
    # endregion

if __name__ == '__main__':
    # rws = RWS(url='192.168.125.1')
    # rws.pptoRoutine('VibrationTest','IRB1100_Vibration_Test')
    # print(rws.excuseRapid())
    rws = RWS()
    print(rws.uploadfile(path='temp/ABB.txt',content='ABBTEST was the best shit!'))
