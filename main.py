import json
import uuid
from twisted.internet import protocol, reactor, endpoints


class RpcProtocol(protocol.Protocol):
    def __init__(self, factory):
        print(1)
        self.factory: RpcServer = factory

    def send(self, data):
        self.transport.write(bytes(json.dumps(data), "UTF8"))

    def dataReceived(self, data):
        try:
            data = json.loads(data)
            print(data)
        except json.JSONDecodeError:
            self.send({"res": "error","error": "not json"})
            return
        if "res" in data:
            return
        match data["type"]:
            case "handshake":
                self.do_handshake(data)
                print(self.factory.services)
            case "respond" if self.role == "service":
                self.factory.make_respond(data["jobid"], data["data"])
            case "request" if self.role == "client":
                try:
                    self.factory.make_request(
                        self, data["service"], data["data"], data["jobid"]
                    )
                    ret = "ok"
                except KeyError:
                    ret = "err"

                ret = {"res": ret, "next_jobid": str(uuid.uuid4())}
                self.send(ret)
            case _:
                self.send({"res": "error", "error": "invalid request"})
                return
    def do_handshake(self, data):
        self.role=data["role"]
        if data["role"] == "client":
            initial_jobid = uuid.uuid4()
            self.send({"res": "ok", "initial_jobid": str(initial_jobid)})
        elif data["role"] == "service":
            for i in data["services"]:
                self.factory.services[i] = self
            self.send({"res": "ok"})

    def make_request(self, service, data, jobid):
        data = {"type": "call", "service": service, "data": data, "jobid": jobid}
        self.send(data)

    def make_respond(self, jobid, data):
        data = {"type": "resp", "data": data, "jobid": jobid}
        self.send(data)


class RpcServer(protocol.Factory):
    services = {}
    promises = {}

    def make_request(self, client, service, data, jobid):
        try:
            self.services[service].make_request(service, data, jobid)
        except KeyError:
            raise KeyError("Not such service")
        self.promises[jobid] = client

    def make_respond(self, jobid, data):
        self.promises[jobid].make_respond(jobid, data)
        del self.promises[jobid]

    def buildProtocol(self, addr):
        return RpcProtocol(self)


endpoints.serverFromString(reactor, "tcp:2474").listen(RpcServer())
reactor.run()
