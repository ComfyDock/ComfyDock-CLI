# comfyenv/cli.py

import os
import sys
import uuid
import json
import yaml
import click
import subprocess
from pathlib import Path
from datetime import datetime
from docker import from_env as docker_from_env
from docker.errors import NotFound

# Initialize Docker client
docker_client = docker_from_env()

# Define paths
HOME_DIR = Path.home()
COMFYENV_DIR = HOME_DIR / ".comfyenv"
CONFIG_FILE = COMFYENV_DIR / "config.yaml"
ENVIRONMENTS_FILE = COMFYENV_DIR / "environments.json"
PROJECTS_DIR = COMFYENV_DIR / "projects"

# Default config
DEFAULT_CONFIG = {
    "default_base_image": "akatz/comfyui-env:v0.3.9-cuda-12.6.2-runtime",
    "default_models_path": str(HOME_DIR / "models"),
    "default_output_path": str(HOME_DIR / "output"),
    "default_input_path": str(HOME_DIR / "input"),
    "default_workflows_path": str(PROJECTS_DIR / "{{env_id}}" / "workflows"),
}

# Ensure ~/.comfyenv and projects directory exist
def ensure_directories():
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'w') as f:
            yaml.dump(DEFAULT_CONFIG, f)
    if not ENVIRONMENTS_FILE.exists():
        with open(ENVIRONMENTS_FILE, 'w') as f:
            json.dump([], f, indent=4)

# Load config
def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return yaml.safe_load(f)

# Save config
def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        yaml.dump(config, f)

# Load environments
def load_environments():
    with open(ENVIRONMENTS_FILE, 'r') as f:
        return json.load(f)

# Save environments
def save_environments(envs):
    with open(ENVIRONMENTS_FILE, 'w') as f:
        json.dump(envs, f, indent=4)

# Generate unique environment ID
def generate_env_id():
    return f"comfy-env-{uuid.uuid4().hex[:8]}"

# Find environment by name or ID
def find_environment(env_identifier):
    envs = load_environments()
    for env in envs:
        if env['id'] == env_identifier or env['name'] == env_identifier:
            return env
    return None

# Initialize global directories and files
ensure_directories()

@click.group()
def cli():
    """Comfyenv CLI Tool"""
    pass

@cli.command()
@click.option('--repo-path', type=click.Path(exists=True, file_okay=False), help='Path to existing ComfyUI repository')
def init(repo_path):
    """Initialize comfyenv with an existing ComfyUI repo path or clone a new one."""
    config = load_config()
    
    if repo_path:
        repo_path = Path(repo_path).resolve()
        if not (repo_path / ".git").exists():
            click.echo("Provided path is not a git repository.")
            sys.exit(1)
    else:
        # Suggest cloning ComfyUI
        default_repo_path = HOME_DIR / "ComfyUI"
        if not default_repo_path.exists():
            click.echo(f"Cloning ComfyUI into {default_repo_path}...")
            subprocess.run(["git", "clone", "https://github.com/comfyui/ComfyUI.git", str(default_repo_path)])
        repo_path = default_repo_path
    
    # Update config with repo path
    config['comfyui_repo_path'] = str(repo_path)
    save_config(config)
    click.echo(f"Comfyenv initialized with ComfyUI repo at {repo_path}")

@cli.command()
@click.argument('env_name')
@click.option('--base-image', default=None, help='Base Docker image to use')
@click.option('--description', default="", help='Description for the environment')
def create(env_name, base_image, description):
    """Create a new comfyenv environment."""
    envs = load_environments()
    existing_env = find_environment(env_name)
    if existing_env:
        click.echo(f"Environment with name or ID '{env_name}' already exists.")
        sys.exit(1)
    
    env_id = generate_env_id()
    base_image = base_image or load_config().get("default_base_image")
    
    # Prompt for base image if not provided
    if not base_image:
        base_image = click.prompt("Enter the base Docker image", default=DEFAULT_CONFIG['default_base_image'])
    
    # Prompt for workflow file name
    workflow_file = click.prompt("Enter the name for the main workflow file", default="default_workflow.json")
    
    # Create project directory
    project_dir = PROJECTS_DIR / env_id
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize .comfyenv.yaml
    comfyenv_file = project_dir / ".comfyenv.yaml"
    comfyenv_data = {
        "name": env_name,
        "description": description,
        "version": 1,
        "docker": {
            "base_image": base_image
        },
        "python_dependencies": [],
        "custom_nodes": [],
        "models": [],
        "env_metadata": {
            "cuda_version": "",
            "python_version": ""
        },
        "workflow": {
            "file": workflow_file
        }
    }
    with open(comfyenv_file, 'w') as f:
        yaml.dump(comfyenv_data, f)
    
    # Initialize Git repo (optional)
    subprocess.run(["git", "init"], cwd=project_dir)
    
    # Add to environments.json
    new_env = {
        "id": env_id,
        "name": env_name,
        "image": base_image,
        "status": "exited",
        "comfyui_path": "",  # Can be filled later if needed
        "command": "--fast",
        "duplicate": False,
        "options": {
            "comfyui_release": "v0.3.4",  # Placeholder, can be updated
            "port": "8188",
            "mount_config": {
                "models": load_config().get("default_models_path"),
                "output": load_config().get("default_output_path"),
                "input": load_config().get("default_input_path")
            },
            "runtime": "nvidia"
        },
        "metadata": {
            "base_image": base_image,
            "created_at": datetime.now().timestamp()
        },
        "folderIds": [
            str(uuid.uuid4())
        ],
        "container_name": env_id
    }
    envs.append(new_env)
    save_environments(envs)
    
    click.echo(f"Environment '{env_name}' with ID '{env_id}' created successfully.")

@cli.command()
def ls():
    """List all comfyenv environments."""
    envs = load_environments()
    if not envs:
        click.echo("No environments found.")
        return
    for env in envs:
        status = env.get("status", "unknown")
        name = env.get("name", "Unnamed")
        env_id = env.get("id", "No ID")
        click.echo(f"[{status.upper()}] {name} (ID: {env_id})")

@cli.command()
@click.argument('env_identifier')
def activate(env_identifier):
    """Activate (start) a comfyenv environment."""
    env = find_environment(env_identifier)
    if not env:
        click.echo(f"Environment '{env_identifier}' not found.")
        sys.exit(1)
    
    if env['status'] == 'running':
        click.echo(f"Environment '{env['name']}' is already running.")
        return
    
    # Pull Docker image if not present
    try:
        docker_client.images.get(env['image'])
        click.echo(f"Docker image '{env['image']}' found locally.")
    except NotFound:
        click.echo(f"Pulling Docker image '{env['image']}'...")
        docker_client.images.pull(env['image'])
    
    # Define mount paths
    mount_config = env['options']['mount_config']
    volumes = {
        mount_config.get("models", load_config().get("default_models_path")): {'bind': '/comfyui/models', 'mode': 'rw'},
        mount_config.get("output", load_config().get("default_output_path")): {'bind': '/comfyui/output', 'mode': 'rw'},
        mount_config.get("input", load_config().get("default_input_path")): {'bind': '/comfyui/input', 'mode': 'rw'},
        # Add more mounts as needed
    }
    
    # Run the container
    container_name = env['container_name']
    try:
        container = docker_client.containers.get(container_name)
        if container.status == 'exited':
            container.start()
            click.echo(f"Started existing container '{container_name}'.")
    except NotFound:
        click.echo(f"Creating and starting container '{container_name}'...")
        container = docker_client.containers.run(
            env['image'],
            name=container_name,
            command=env.get('command', '--fast'),
            ports={'8188/tcp': int(env['options']['port'])},
            volumes=volumes,
            detach=True,
            runtime=env['options'].get('runtime', 'nvidia')
        )
    
    # Update status
    env['status'] = 'running'
    envs = load_environments()
    for e in envs:
        if e['id'] == env['id']:
            e['status'] = 'running'
            break
    save_environments(envs)
    
    click.echo(f"Environment '{env['name']}' is now active and running.")

@cli.command()
@click.argument('env_identifier')
def deactivate(env_identifier):
    """Deactivate (stop) a comfyenv environment."""
    env = find_environment(env_identifier)
    if not env:
        click.echo(f"Environment '{env_identifier}' not found.")
        sys.exit(1)
    
    if env['status'] != 'running':
        click.echo(f"Environment '{env['name']}' is not running.")
        return
    
    container_name = env['container_name']
    try:
        container = docker_client.containers.get(container_name)
        container.stop()
        click.echo(f"Stopped container '{container_name}'.")
    except NotFound:
        click.echo(f"Container '{container_name}' not found.")
    
    # Update status
    env['status'] = 'exited'
    envs = load_environments()
    for e in envs:
        if e['id'] == env['id']:
            e['status'] = 'exited'
            break
    save_environments(envs)

@cli.command()
@click.argument('env_identifier')
@click.option('--workflow-file', default=None, help='Specify the main workflow file to include')
@click.option('--out', default=None, help='Output path for the .comfyenv.yaml file')
def pack(env_identifier, workflow_file, out):
    """Pack the current environment into a .comfyenv.yaml file."""
    env = find_environment(env_identifier)
    if not env:
        click.echo(f"Environment '{env_identifier}' not found.")
        sys.exit(1)
    
    if env['status'] != 'running':
        click.echo(f"Environment '{env['name']}' is not running. Please activate it first.")
        sys.exit(1)
    
    container_name = env['container_name']
    try:
        container = docker_client.containers.get(container_name)
    except NotFound:
        click.echo(f"Container '{container_name}' not found.")
        sys.exit(1)
    
    # Execute pip freeze inside the container
    click.echo("Gathering Python dependencies...")
    pip_freeze = container.exec_run("pip freeze", demux=True)
    if pip_freeze.exit_code != 0:
        click.echo("Failed to run pip freeze inside the container.")
        sys.exit(1)
    python_dependencies = pip_freeze.output[0].decode().splitlines()
    
    # Gather custom nodes
    click.echo("Gathering custom nodes information...")
    custom_nodes = []
    try:
        custom_nodes_list = container.exec_run("ls /comfyui/custom_nodes", demux=True)
        if custom_nodes_list.exit_code == 0:
            node_dirs = custom_nodes_list.output[0].decode().splitlines()
            for node_dir in node_dirs:
                # Check if it's a git repo
                is_git = container.exec_run(f"test -d /comfyui/custom_nodes/{node_dir}/.git && echo 'yes' || echo 'no'", demux=True).output[0].decode().strip()
                if is_git == 'yes':
                    repo_url = container.exec_run(f"git -C /comfyui/custom_nodes/{node_dir} config --get remote.origin.url", demux=True).output[0].decode().strip()
                    commit_hash = container.exec_run(f"git -C /comfyui/custom_nodes/{node_dir} rev-parse HEAD", demux=True).output[0].decode().strip()
                    custom_nodes.append({
                        "name": node_dir,
                        "repo_url": repo_url,
                        "version": f"commit:{commit_hash}"
                    })
                else:
                    # Non-git custom node
                    custom_nodes.append({
                        "name": node_dir,
                        "repo_url": "",
                        "version": ""
                    })
    except Exception as e:
        click.echo(f"Error gathering custom nodes: {e}")
    
    # Gather models
    click.echo("Gathering model files...")
    models = []
    try:
        models_dirs = container.exec_run("ls /comfyui/models", demux=True).output[0].decode().splitlines()
        for model_dir in models_dirs:
            # List files in each model type directory
            model_files = container.exec_run(f"ls /comfyui/models/{model_dir}", demux=True).output[0].decode().splitlines()
            for model_file in model_files:
                # Compute SHA256 inside the container
                sha256 = container.exec_run(f"sha256sum /comfyui/models/{model_dir}/{model_file} | awk '{{print $1}}'", demux=True).output[0].decode().strip()
                model_type = model_dir  # Assuming model_dir corresponds to type
                models.append({
                    "name": model_file,
                    "hash": f"sha256:{sha256}",
                    "type": model_type
                })
    except Exception as e:
        click.echo(f"Error gathering models: {e}")
    
    # Gather workflow file
    if not workflow_file:
        # Attempt to detect the workflow file
        try:
            workflows_list = container.exec_run("ls /comfyui/workflows", demux=True)
            if workflows_list.exit_code == 0:
                workflow_files = workflows_list.output[0].decode().splitlines()
                if len(workflow_files) == 1:
                    workflow_file = workflow_files[0]
                elif len(workflow_files) > 1:
                    click.echo("Multiple workflow files detected. Please specify which one to pack.")
                    for wf in workflow_files:
                        click.echo(f"- {wf}")
                    workflow_file = click.prompt("Enter the workflow file to pack", type=str)
                else:
                    click.echo("No workflow files found. Please create one before packing.")
                    sys.exit(1)
        except Exception as e:
            click.echo(f"Error detecting workflow file: {e}")
            sys.exit(1)
    
    # Prepare .comfyenv.yaml data
    comfyenv_data = {
        "name": env['name'],
        "description": env.get("description", ""),
        "version": 1,
        "docker": {
            "base_image": env['image']
        },
        "python_dependencies": python_dependencies,
        "custom_nodes": custom_nodes,
        "models": models,
        "env_metadata": {
            "cuda_version": env['options'].get("cuda_version", ""),
            "python_version": env['options'].get("python_version", "")
        },
        "workflow": {
            "file": workflow_file
        }
    }
    
    # Write to .comfyenv.yaml
    out_path = out or (PROJECTS_DIR / env['id'] / ".comfyenv.yaml")
    with open(out_path, 'w') as f:
        yaml.dump(comfyenv_data, f)
    
    click.echo(f".comfyenv.yaml packed successfully at {out_path}")

@cli.command()
@click.argument('env_identifier')
def restore(env_identifier):
    """Restore an environment from a .comfyenv.yaml file."""
    env = find_environment(env_identifier)
    if not env:
        click.echo(f"Environment '{env_identifier}' not found.")
        sys.exit(1)
    
    comfyenv_file = PROJECTS_DIR / env['id'] / ".comfyenv.yaml"
    if not comfyenv_file.exists():
        click.echo(f".comfyenv.yaml file not found for environment '{env['name']}'.")
        sys.exit(1)
    
    # Load .comfyenv.yaml
    with open(comfyenv_file, 'r') as f:
        comfyenv_data = yaml.safe_load(f)
    
    # Pull Docker image if not present
    try:
        docker_client.images.get(comfyenv_data['docker']['base_image'])
        click.echo(f"Docker image '{comfyenv_data['docker']['base_image']}' found locally.")
    except NotFound:
        click.echo(f"Pulling Docker image '{comfyenv_data['docker']['base_image']}'...")
        docker_client.images.pull(comfyenv_data['docker']['base_image'])
    
    # Define mount paths
    mount_config = env['options']['mount_config']
    volumes = {
        mount_config.get("models", load_config().get("default_models_path")): {'bind': '/comfyui/models', 'mode': 'rw'},
        mount_config.get("output", load_config().get("default_output_path")): {'bind': '/comfyui/output', 'mode': 'rw'},
        mount_config.get("input", load_config().get("default_input_path")): {'bind': '/comfyui/input', 'mode': 'rw'},
        # Add more mounts as needed
    }
    
    # Run the container
    container_name = env['container_name']
    try:
        container = docker_client.containers.get(container_name)
        if container.status == 'exited':
            container.start()
            click.echo(f"Started existing container '{container_name}'.")
    except NotFound:
        click.echo(f"Creating and starting container '{container_name}'...")
        container = docker_client.containers.run(
            comfyenv_data['docker']['base_image'],
            name=container_name,
            command=env.get('command', '--fast'),
            ports={'8188/tcp': int(env['options']['port'])},
            volumes=volumes,
            detach=True,
            runtime=env['options'].get('runtime', 'nvidia')
        )
    
    # Clone custom nodes
    click.echo("Cloning custom nodes...")
    for node in comfyenv_data.get("custom_nodes", []):
        if node['repo_url']:
            subprocess.run(["git", "clone", node['repo_url'], f"/comfyui/custom_nodes/{node['name']}"], 
                           cwd=PROJECTS_DIR / env['id'])
            subprocess.run(["git", "checkout", node['version'].split(':')[1]], 
                           cwd=PROJECTS_DIR / env['id'] / "custom_nodes" / node['name'])
    
    # Install Python dependencies
    click.echo("Installing Python dependencies...")
    pip_requirements = "\n".join(comfyenv_data.get("python_dependencies", []))
    with open(PROJECTS_DIR / env['id'] / "requirements.txt", 'w') as f:
        f.write(pip_requirements)
    subprocess.run(["pip", "install", "-r", "requirements.txt"], 
                   cwd=PROJECTS_DIR / env['id'],
                   shell=True)
    
    # Update status
    env['status'] = 'running'
    envs = load_environments()
    for e in envs:
        if e['id'] == env['id']:
            e['status'] = 'running'
            break
    save_environments(envs)
    
    click.echo(f"Environment '{env['name']}' has been restored and is now running.")

@cli.command()
@click.argument('env_identifier')
def delete(env_identifier):
    """Delete a comfyenv environment and its associated container."""
    env = find_environment(env_identifier)
    if not env:
        click.echo(f"Environment '{env_identifier}' not found.")
        sys.exit(1)
    
    # Stop the container if running
    if env['status'] == 'running':
        container_name = env['container_name']
        try:
            container = docker_client.containers.get(container_name)
            container.stop()
            click.echo(f"Stopped container '{container_name}'.")
        except NotFound:
            click.echo(f"Container '{container_name}' not found.")
    
    # Remove the container
    try:
        container = docker_client.containers.get(env['container_name'])
        container.remove()
        click.echo(f"Removed container '{container_name}'.")
    except NotFound:
        pass  # Already handled
    
    # Remove from environments.json
    envs = load_environments()
    envs = [e for e in envs if e['id'] != env['id']]
    save_environments(envs)
    
    # Remove project directory
    project_dir = PROJECTS_DIR / env['id']
    if project_dir.exists():
        subprocess.run(["rm", "-rf", str(project_dir)])
        click.echo(f"Removed project directory '{project_dir}'.")
    
    click.echo(f"Environment '{env['name']}' has been deleted.")

@cli.command()
def status():
    """Show the status of all comfyenv environments."""
    envs = load_environments()
    if not envs:
        click.echo("No environments found.")
        return
    for env in envs:
        click.echo(f"Name: {env['name']}")
        click.echo(f"ID: {env['id']}")
        click.echo(f"Status: {env['status']}")
        click.echo(f"Container: {env['container_name']}")
        click.echo(f"Base Image: {env['image']}")
        created_at = datetime.fromtimestamp(env['metadata']['created_at']).strftime('%Y-%m-%d %H:%M:%S')
        click.echo(f"Created At: {created_at}")
        click.echo("-" * 40)

@cli.command()
def config():
    """Show the current comfyenv configuration."""
    config = load_config()
    click.echo("Current comfyenv configuration:")
    click.echo(yaml.dump(config))
    # Optionally, add interactive editing in future

if __name__ == '__main__':
    cli()
