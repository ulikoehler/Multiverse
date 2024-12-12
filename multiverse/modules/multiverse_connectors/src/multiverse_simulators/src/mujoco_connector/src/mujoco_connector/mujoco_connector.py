#!/usr/bin/env python3

"""Multiverse Mujoco Connector class"""

import os
import xml.etree.ElementTree as ET

import jax
import mujoco
import mujoco.viewer
import numpy
from mujoco import mjx

from multiverse_simulator import MultiverseSimulator, MultiverseRenderer, MultiverseViewer
from .utills import get_multiverse_connector_plugin


class MultiverseMujocoRenderer(MultiverseRenderer):
    """Multiverse Isaac Sim Renderer class"""

    def __init__(self, mj_viewer: mujoco.viewer):
        self._mj_viewer = mj_viewer
        super().__init__()

    def is_running(self) -> bool:
        return self.mj_viewer.is_running()

    def close(self):
        self.mj_viewer.close()

    @property
    def mj_viewer(self) -> mujoco.viewer:
        return self._mj_viewer


class MultiverseMujocoConnector(MultiverseSimulator):
    """Multiverse MuJoCo Connector class"""

    use_mjx: bool = False
    """Use MJX (https://mujoco.readthedocs.io/en/stable/mjx.html)"""

    def __init__(self, file_path: str, viewer: MultiverseViewer = None, number_of_instances: int = 1, **kwargs):
        self._file_path = file_path
        root = ET.parse(file_path).getroot()
        self.name = root.attrib.get("model", self.name)
        self.use_mjx = kwargs.get("use_mjx", False)
        super().__init__(viewer, number_of_instances, **kwargs)
        mujoco.mj_loadPluginLibrary(get_multiverse_connector_plugin())
        assert os.path.exists(self.file_path)
        self._mj_model = mujoco.MjModel.from_xml_path(filename=self.file_path)
        assert self._mj_model is not None
        self._mj_model.opt.timestep = self.step_size
        self._mj_data = mujoco.MjData(self._mj_model)
        if self.use_mjx:
            self._mjx_model = mjx.put_model(self._mj_model)
            self._mjx_data = mjx.put_data(self._mj_model, self._mj_data)
            self._batch = jax.vmap(lambda ctrl0: self._mjx_data.replace(ctrl=ctrl0))(
                ctrl0=numpy.array([[0.0 for _ in range(self._mj_model.nu)] for _ in range(number_of_instances)]))
            self._jit_step = jax.jit(jax.vmap(mjx.step, in_axes=(None, 0)))

    def start_callback(self):
        if not self.headless:
            self._renderer = mujoco.viewer.launch_passive(self._mj_model, self._mj_data)
        else:
            self._renderer = MultiverseRenderer()

    def step_callback(self):
        if self.use_mjx:
            self._batch = self._jit_step(self._mjx_model, self._batch)
            if not self.headless:
                self._mj_data = mjx.get_data(self._mj_model, self._batch)
        else:
            mujoco.mj_step(self._mj_model, self._mj_data)

    def reset_callback(self):
        if self.use_mjx:
            pass  # TODO: Implement reset_callback for MJX
        else:
            mujoco.mj_resetDataKeyframe(self._mj_model, self._mj_data, 0)

    def write_data_to_simulator(self, write_data: numpy.ndarray):
        if not self.use_mjx and write_data.shape[0] > 1:
            raise NotImplementedError("Multiple instances for non MJX is not supported yet")
        if self.use_mjx:
            ctrl = numpy.array(self._batch.ctrl)
            qpos = numpy.array(self._batch.qpos)
        else:
            ctrl = self._mj_data.ctrl
            qpos = self._mj_data.qpos
        for instance_id, data in enumerate(write_data):
            i = 0
            for name, attrs in self._viewer.send_objects.items():
                for attr in attrs:
                    if attr.name in {"joint_rvalue", "joint_tvalue"}:
                        joint_id = self._mj_data.joint(name).id
                        if self.use_mjx:
                            qpos[instance_id][joint_id] = data[i]
                        else:
                            qpos[joint_id] = data[i]
                    elif attr.name in {"cmd_joint_rvalue", "cmd_joint_angular_velocity", "cmd_joint_torque",
                                     "cmd_joint_tvalue", "cmd_joint_linear_velocity", "cmd_joint_force"}:
                        actuator_id = self._mj_data.actuator(name).id
                        if self.use_mjx:
                            ctrl[instance_id][actuator_id] = data[i]
                        else:
                            ctrl[actuator_id] = data[i]
                    else:
                        raise ValueError(f"Unknown attribute {attr.name} for object {name}")
                    i += 1
            if i != len(data):
                raise ValueError(f"Data length mismatch (expected {len(data)}, got {i})")
            if self.use_mjx:
                self._batch = self._batch.replace(qpos=qpos, ctrl=ctrl)
            else:
                self._mj_data.ctrl = ctrl

    def read_data_from_simulator(self, read_data: numpy.ndarray):
        if not self.use_mjx and read_data.shape[0] > 1:
            raise NotImplementedError("Multiple instances for non MJX is not supported yet")
        for instance_id, data in enumerate(read_data):
            i = 0
            for name, attrs in self._viewer.receive_objects.items():
                for attr in attrs:
                    if attr.name in {"joint_rvalue", "joint_tvalue"}:
                        joint_id = self._mj_data.joint(name).id
                        if self.use_mjx:
                            read_data[instance_id][i] = self._batch.qpos[instance_id][joint_id]
                        else:
                            read_data[instance_id][i] = self._mj_data.qpos[joint_id]
                    elif attr.name in {"joint_angular_velocity", "joint_linear_velocity"}:
                        joint_id = self._mj_data.joint(name).id
                        if self.use_mjx:
                            read_data[instance_id][i] = self._batch.qvel[instance_id][joint_id]
                        else:
                            read_data[instance_id][i] = self._mj_data.qvel[joint_id]
                    elif attr.name in {"joint_torque", "joint_force"}:
                        joint_id = self._mj_data.joint(name).id
                        if self.use_mjx:
                            read_data[instance_id][i] = self._batch.qfrc_applied[instance_id][joint_id]
                        else:
                            read_data[instance_id][i] = self._mj_data.qfrc_applied[joint_id]
                    elif attr.name in {"cmd_joint_rvalue", "cmd_joint_angular_velocity", "cmd_joint_torque",
                                     "cmd_joint_tvalue", "cmd_joint_linear_velocity", "cmd_joint_force"}:
                        actuator_id = self._mj_data.actuator(name).id
                        if self.use_mjx:
                            read_data[instance_id][i] = self._batch.ctrl[instance_id][actuator_id]
                        else:
                            read_data[instance_id][i] = self._mj_data.ctrl[actuator_id]
                    else:
                        self.log_error(f"Unknown attribute {attr.name} for object {name}")
                    i += 1
            if i != len(data):
                raise ValueError(f"Data length mismatch (expected {len(data)}, got {i})")

    @property
    def file_path(self) -> str:
        return self._file_path

    @property
    def current_simulation_time(self) -> float:
        return self._mj_data.time if not self.use_mjx else self._batch.time[0]

    @property
    def renderer(self):
        return self._renderer
