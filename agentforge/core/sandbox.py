# docker container runner, which will executes code safely

import docker

def create_hardened_sandbox(host_workspace_dir: str):
    client = docker.from_env()
    return client.containers.run(
        image="agentforge-sandbox:latest",
        command="sleep 3600",
        detach=True,
        mem_limit="1024m",
        pids_limit=100,
        read_only=True,
        volumes={host_workspace_dir: {"bind": "/workspace", "mode": "rw"}},
        tmpfs={"/tmp": "size=128m,mode=1777"},
        working_dir="/workspace",
        user="sandboxuser",
        security_opt=["no-new-privileges:true"],
        cap_drop=["ALL"],
        network_mode="none",
    )