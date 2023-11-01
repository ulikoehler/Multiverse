#!/usr/bin/env python3

from multiverse_socket.utils import init_request_meta_data_dict
import rospy
from typing import List, Dict
from multiverse_client_pybind import MultiverseClientPybind  # noqa


class MultiverseRosBase:
    _request_meta_data_dict = {}

    def __init__(self, **kwargs) -> None:
        self.host = str(rospy.get_param(param_name="/multiverse_server/host", default="tcp://127.0.0.1"))
        self.port = str(kwargs.get("port"))
        self.world = str(kwargs.get("world", "world"))
        self._init_request_meta_data()

    def start(self) -> None:
        pass

    def _init_multiverse_socket(self) -> None:
        if rospy.has_param("/multiverse_server/port"):
            server_socket_addr = self.host + ":" + str(rospy.get_param("/multiverse_server/port"))
        else:
            server_socket_addr = self.host + ":7000"
        self.__multiverse_socket = MultiverseClientPybind(server_socket_addr)

    def _init_request_meta_data(self) -> None:
        self._request_meta_data_dict = init_request_meta_data_dict(self.world)

    def _connect(self) -> None:
        self.__multiverse_socket.connect(self.host, self.port)
        self.__multiverse_socket.start()

    def _disconnect(self) -> None:
        self.__multiverse_socket.disconnect()

    def _set_request_meta_data(self) -> None:
        self.__multiverse_socket.set_request_meta_data(self._request_meta_data_dict)

    def _get_response_meta_data(self) -> Dict:
        response_meta_data = self.__multiverse_socket.get_response_meta_data()
        if not response_meta_data:
            rospy.logwarn(f"[Client {self.port}] Receive empty response meta data.")
        return response_meta_data

    def _set_send_data(self, send_data: List[float]) -> None:
        self.__multiverse_socket.set_send_data(send_data)

    def _communicate(self, resend_request_meta_data: bool = False) -> None:
        self.__multiverse_socket.communicate(resend_request_meta_data)

    def _get_receive_data(self) -> List[float]:
        receive_data = self.__multiverse_socket.get_receive_data()
        if not receive_data:
            rospy.logwarn(f"[Client {self.port}] Receive empty data.")
        return receive_data

    def _restart(self) -> None:
        self._disconnect()
        self._connect()
