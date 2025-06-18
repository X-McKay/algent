#!/usr/bin/env python3
"""
Agentic System CLI - Beautiful command-line interface for managing the agentic system
Built with Typer for modern Python CLI development
"""
import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import typer
import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Prompt, Confirm
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.tree import Tree
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.status import Status

# Initialize Rich console
console = Console()

# Initialize Typer app
app = typer.Typer(
    name="agentic",
    help="🤖 Agentic System CLI - Manage your AI agent infrastructure",
    rich_markup_mode="rich",
    add_completion=False,
    no_args_is_help=True
)

# Configuration
DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_MCP_URL = "http://localhost:8080"
CONFIG_FILE = Path.home() / ".agentic" / "config.json"

class AgentType(str, Enum):
    """Available agent types"""
    calculator = "calculator"
    echo = "echo"
    file_processor = "file_processor"

class LogLevel(str, Enum):
    """Log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

class AgenticConfig:
    """Configuration management for the CLI"""
    
    def __init__(self):
        self.config_dir = Path.home() / ".agentic"
        self.config_file = self.config_dir / "config.json"
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Default configuration
        return {
            "api_url": DEFAULT_API_URL,
            "mcp_url": DEFAULT_MCP_URL,
            "timeout": 30,
            "auto_start": False,
            "preferred_editor": "nano",
            "log_level": "INFO"
        }
    
    def save_config(self):
        """Save configuration to file"""
        self.config_dir.mkdir(exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        self.config[key] = value
        self.save_config()

# Global config instance
config = AgenticConfig()

class EarthlyManager:
    """Earthly and Docker Compose operations manager"""
    
    def __init__(self):
        self.earthfile = Path("Earthfile")
        self.compose_file = Path("docker-compose-earthly.yml")
    
    def check_earthly(self) -> bool:
        """Check if Earthly is available"""
        try:
            subprocess.run(["earthly", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def check_docker_compose(self) -> bool:
        """Check if docker-compose is available"""
        try:
            subprocess.run(["docker-compose", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def run_earthly_command(self, command: List[str], capture_output: bool = False) -> subprocess.CompletedProcess:
        """Run an Earthly command"""
        cmd = ["earthly"] + command
        if capture_output:
            return subprocess.run(cmd, capture_output=True, text=True)
        else:
            return subprocess.run(cmd)
    
    def run_compose_command(self, command: List[str], capture_output: bool = False, use_earthly_compose: bool = True) -> subprocess.CompletedProcess:
        """Run a docker-compose command"""
        compose_file = "docker-compose-earthly.yml" if use_earthly_compose else "docker-compose.yml"
        cmd = ["docker-compose", "-f", compose_file, "--env-file", ".env"] + command
        if capture_output:
            return subprocess.run(cmd, capture_output=True, text=True)
        else:
            return subprocess.run(cmd)
    
    def build_images(self, clean: bool = False, no_cache: bool = False) -> bool:
        """Build images using Earthly"""
        if not self.check_earthly():
            return False
        
        if clean:
            subprocess.run(["docker", "system", "prune", "-f"], capture_output=True)
        
        build_cmd = ["+all"]
        if no_cache:
            build_cmd.append("--no-cache")
        
        result = self.run_earthly_command(build_cmd)
        return result.returncode == 0
    
    def start_infrastructure(self) -> bool:
        """Start infrastructure services (redis, postgres)"""
        if not self.check_docker_compose():
            return False
        
        result = self.run_compose_command(["up", "-d", "redis", "postgres"], use_earthly_compose=True)
        return result.returncode == 0
    
    def start_services(self) -> bool:
        """Start application services"""
        if not self.check_docker_compose():
            return False
        
        result = self.run_compose_command(["up", "-d", "api-server", "file-processor", "agent-runner"], use_earthly_compose=True)
        return result.returncode == 0
    
    def stop_all(self, remove_volumes: bool = False) -> bool:
        """Stop all services"""
        if not self.check_docker_compose():
            return False
        
        cmd = ["down"]
        if remove_volumes:
            cmd.append("-v")
        
        result = self.run_compose_command(cmd, use_earthly_compose=True)
        return result.returncode == 0
    
    def restart_services(self, service: Optional[str] = None) -> bool:
        """Restart services"""
        if not self.check_docker_compose():
            return False
        
        cmd = ["restart"]
        if service:
            cmd.append(service)
        
        result = self.run_compose_command(cmd, use_earthly_compose=True)
        return result.returncode == 0
    
    def get_logs(self, service: Optional[str] = None, follow: bool = False, tail: int = 100) -> bool:
        """Get service logs"""
        if not self.check_docker_compose():
            return False
        
        cmd = ["logs"]
        if follow:
            cmd.append("-f")
        if tail:
            cmd.extend(["--tail", str(tail)])
        if service:
            cmd.append(service)
        
        result = self.run_compose_command(cmd, use_earthly_compose=True)
        return result.returncode == 0
    
    def open_shell(self, service: str = "api-server") -> bool:
        """Open shell in service container"""
        if not self.check_docker_compose():
            return False
        
        result = self.run_compose_command(["exec", service, "/bin/bash"], use_earthly_compose=True)
        return result.returncode == 0
    
    def get_service_status(self) -> List[Dict[str, str]]:
        """Get status of all services"""
        try:
            result = self.run_compose_command(["ps", "--format", "json"], capture_output=True, use_earthly_compose=True)
            if result.returncode == 0 and result.stdout.strip():
                services = []
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            service_data = json.loads(line)
                            services.append({
                                "name": service_data.get("Service", "unknown"),
                                "state": service_data.get("State", "unknown"),
                                "status": f"{service_data.get('Status', 'unknown')} ({service_data.get('Health', 'no health check')})",
                                "ports": service_data.get("Publishers", [])
                            })
                        except json.JSONDecodeError:
                            continue
                return services
        except Exception:
            pass
        
        # Fallback to regular docker ps
        try:
            result = subprocess.run(["docker", "ps", "--format", "json", "--filter", "name=algent-"], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                services = []
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            container_data = json.loads(line)
                            services.append({
                                "name": container_data.get("Names", "unknown").replace('algent-', ''),
                                "state": "running" if container_data.get("State") == "running" else "stopped",
                                "status": container_data.get("Status", "unknown"),
                                "ports": container_data.get("Ports", "")
                            })
                        except json.JSONDecodeError:
                            continue
                return services
        except Exception:
            pass
        
        return []

# Replace DockerManager with EarthlyManager in the code
docker_mgr = EarthlyManager()

class ApiClient:
    """HTTP client for API interactions"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or config.get("api_url", DEFAULT_API_URL)
        self.timeout = config.get("timeout", 30)
    
    async def get(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Make GET request"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}{endpoint}")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            console.print(f"[red]API Error: {e}[/red]")
            return None
    
    async def post(self, endpoint: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make POST request"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}{endpoint}", json=data)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            console.print(f"[red]API Error: {e}[/red]")
            return None
    
    async def delete(self, endpoint: str) -> bool:
        """Make DELETE request"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(f"{self.base_url}{endpoint}")
                response.raise_for_status()
                return True
        except Exception:
            return False

# Global API client instance
api = ApiClient()

def show_dashboard():
    """Show the main dashboard"""
    console.clear()
    
    # Header
    console.print(Panel.fit(
        "[bold blue]🤖 Agentic System Dashboard[/bold blue]\n"
        "[dim]Distributed AI Agent Infrastructure Management[/dim]",
        title="🚀 Welcome"
    ))
    
    # Quick status
    docker_mgr = EarthlyManager()
    services = docker_mgr.get_service_status()
    
    if services:
        table = Table(title="📊 Service Status", show_header=True, header_style="bold magenta")
        table.add_column("Service", style="cyan")
        table.add_column("State", justify="center")
        table.add_column("Status", style="dim")
        
        for service in services:
            state_color = "green" if service["state"] == "running" else "red"
            table.add_row(
                service["name"],
                f"[{state_color}]{service['state']}[/{state_color}]",
                service["status"][:50] + "..." if len(service["status"]) > 50 else service["status"]
            )
        
        console.print(table)
    else:
        console.print("[yellow]No services detected. Run 'agentic start' to begin.[/yellow]")
    
    # Quick actions
    console.print("\n[bold]🚀 Quick Actions:[/bold]")
    console.print("  • [cyan]agentic start[/cyan]         - Start all services")
    console.print("  • [cyan]agentic agents list[/cyan]   - List active agents")
    console.print("  • [cyan]agentic docker logs[/cyan]   - View service logs")
    console.print("  • [cyan]agentic monitor[/cyan]       - Real-time monitoring")
    console.print("  • [cyan]agentic --help[/cyan]        - Show all commands")

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Show version information")
):
    """
    🤖 Agentic System CLI - Manage your AI agent infrastructure
    
    A beautiful command-line interface for building, deploying, and managing 
    your distributed agentic system with A2A communication and MCP integration.
    """
    if version:
        console.print(Panel.fit(
            "[bold blue]Agentic System CLI[/bold blue]\n"
            "Version: 1.0.0\n"
            "Python: 3.13.5 • Ubuntu: 24.04 • Earthly: Latest\n"
            "Built with ❤️  for the AI agent community",
            title="🤖 Version Info"
        ))
        return
    
    if ctx.invoked_subcommand is None:
        show_dashboard()

# Docker commands group
docker_app = typer.Typer(name="docker", help="🐳 Docker and container management")
app.add_typer(docker_app, name="docker")

@docker_app.command("build")
def docker_build(
    clean: bool = typer.Option(False, "--clean", help="Clean build (remove old images)"),
    parallel: bool = typer.Option(True, "--parallel/--no-parallel", help="Build in parallel"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Build without cache")
):
    """🏗️ Build all Earthly targets"""
    docker_mgr = EarthlyManager()
    
    if not docker_mgr.check_earthly():
        console.print("[red]❌ Earthly is not available. Please install Earthly first.[/red]")
        console.print("[blue]💡 Visit: https://earthly.dev/get-earthly[/blue]")
        raise typer.Exit(1)
    
    console.print(Panel.fit(
        "[bold blue]🏗️ Building Agentic System Images[/bold blue]\n"
        "Ubuntu 24.04 • Python 3.13.5 • Optimized Dependencies",
        title="🌍 Earthly Build"
    ))
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("🔨 Building images...", total=100)
        
        try:
            success = docker_mgr.build_images(clean=clean, no_cache=no_cache)
            progress.update(task, completed=100)
            
            if success:
                console.print("[green]✅ Build completed successfully![/green]")
            else:
                console.print("[red]❌ Build failed![/red]")
                raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]❌ Build error: {e}[/red]")
            raise typer.Exit(1)

@docker_app.command("start")
def docker_start(
    detach: bool = typer.Option(True, "-d", "--detach", help="Run in detached mode"),
    build: bool = typer.Option(False, "--build", help="Build images before starting"),
    infrastructure_only: bool = typer.Option(False, "--infra-only", help="Start only infrastructure services")
):
    """🚀 Start all services"""
    docker_mgr = EarthlyManager()
    
    if not docker_mgr.check_earthly() or not docker_mgr.check_docker_compose():
        console.print("[red]❌ Earthly and docker-compose are required[/red]")
        raise typer.Exit(1)
    
    console.print(Panel.fit(
        "[bold green]🚀 Starting Agentic System[/bold green]\n"
        "Initializing agents, message bus, and API services...",
        title="🌍 Service Startup"
    ))
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        if build:
            task = progress.add_task("🔨 Building images...", total=None)
            if not docker_mgr.build_images():
                console.print("[red]❌ Failed to build images[/red]")
                raise typer.Exit(1)
            progress.remove_task(task)
        
        task1 = progress.add_task("🚀 Starting infrastructure (Redis, PostgreSQL)...", total=None)
        if not docker_mgr.start_infrastructure():
            console.print("[red]❌ Failed to start infrastructure[/red]")
            raise typer.Exit(1)
        progress.remove_task(task1)
        
        if not infrastructure_only:
            task2 = progress.add_task("⏳ Waiting for infrastructure...", total=None)
            time.sleep(10)
            progress.remove_task(task2)
            
            task3 = progress.add_task("🤖 Starting application services...", total=None)
            if not docker_mgr.start_services():
                console.print("[red]❌ Failed to start application services[/red]")
                raise typer.Exit(1)
            progress.remove_task(task3)
            
            task4 = progress.add_task("🔍 Health checking...", total=None)
            time.sleep(15)
            progress.remove_task(task4)
    
    if infrastructure_only:
        console.print("[green]✅ Infrastructure services started![/green]")
    else:
        console.print("[green]✅ All services started![/green]")
        
        # Show access information
        console.print(Panel.fit(
            "[bold]🌐 Access Points:[/bold]\n"
            "• API Server: http://localhost:8000\n"
            "• API Documentation: http://localhost:8000/docs\n"
            "• Health Check: http://localhost:8000/health\n"
            "• PostgreSQL: localhost:5432\n"
            "• Redis: localhost:6379",
            title="🔗 Quick Access"
        ))

@docker_app.command("stop")
def docker_stop(
    volumes: bool = typer.Option(False, "-v", "--volumes", help="Remove volumes as well")
):
    """🛑 Stop all services"""
    docker_mgr = EarthlyManager()
    
    if not docker_mgr.check_docker_compose():
        console.print("[red]❌ docker-compose is not available[/red]")
        raise typer.Exit(1)
    
    with console.status("[bold red]Stopping services..."):
        success = docker_mgr.stop_all(remove_volumes=volumes)
    
    if success:
        console.print("[yellow]🛑 All services stopped[/yellow]")
    else:
        console.print("[red]❌ Failed to stop services[/red]")
        raise typer.Exit(1)

@docker_app.command("logs")
def docker_logs(
    service: Optional[str] = typer.Argument(None, help="Service name to view logs for"),
    follow: bool = typer.Option(False, "-f", "--follow", help="Follow log output"),
    tail: int = typer.Option(100, "--tail", help="Number of lines to show")
):
    """📋 View service logs"""
    docker_mgr = EarthlyManager()
    
    if not docker_mgr.check_docker_compose():
        console.print("[red]❌ docker-compose is not available[/red]")
        raise typer.Exit(1)
    
    console.print(f"[blue]📋 Viewing logs{' for ' + service if service else ''}...[/blue]")
    docker_mgr.get_logs(service=service, follow=follow, tail=tail)

@docker_app.command("status")
def docker_status():
    """📊 Show detailed service status"""
    docker_mgr = EarthlyManager()
    services = docker_mgr.get_service_status()
    
    if not services:
        console.print("[yellow]No services running[/yellow]")
        console.print("[blue]💡 Run 'agentic start' to start services[/blue]")
        return
    
    table = Table(title="📊 Detailed Service Status", show_header=True, header_style="bold magenta")
    table.add_column("Service", style="cyan", width=20)
    table.add_column("State", justify="center", width=12)
    table.add_column("Status", style="dim", width=40)
    table.add_column("Ports", style="blue", width=20)
    
    for service in services:
        state_color = "green" if service["state"] == "running" else "red"
        ports = str(service.get("ports", ""))[:20] if service.get("ports") else "None"
        
        table.add_row(
            service["name"],
            f"[{state_color}]{service['state']}[/{state_color}]",
            service["status"][:40] + "..." if len(service["status"]) > 40 else service["status"],
            ports
        )
    
    console.print(table)

@docker_app.command("restart")
def docker_restart(
    service: Optional[str] = typer.Argument(None, help="Service to restart (all if not specified)")
):
    """🔄 Restart services"""
    docker_mgr = EarthlyManager()
    
    if not docker_mgr.check_docker_compose():
        console.print("[red]❌ docker-compose is not available[/red]")
        raise typer.Exit(1)
    
    with console.status(f"[bold yellow]Restarting {service or 'all services'}..."):
        success = docker_mgr.restart_services(service=service)
    
    if success:
        console.print(f"[green]✅ {service or 'All services'} restarted![/green]")
    else:
        console.print(f"[red]❌ Failed to restart {service or 'services'}[/red]")
        raise typer.Exit(1)

@docker_app.command("shell")
def docker_shell(
    service: str = typer.Argument("api-server", help="Service to open shell in")
):
    """🐚 Open interactive shell in a service container"""
    docker_mgr = EarthlyManager()
    
    if not docker_mgr.check_docker_compose():
        console.print("[red]❌ docker-compose is not available[/red]")
        raise typer.Exit(1)
    
    console.print(f"[blue]🐚 Opening shell in {service}...[/blue]")
    
    try:
        docker_mgr.open_shell(service)
    except KeyboardInterrupt:
        console.print("\n[yellow]Shell session ended[/yellow]")

# Agents commands group
agents_app = typer.Typer(name="agents", help="🤖 Agent management and interaction")
app.add_typer(agents_app, name="agents")

@agents_app.command("list")
def agents_list():
    """📋 List all active agents"""
    async def _list_agents():
        api = ApiClient()
        
        with console.status("[bold blue]Fetching agents..."):
            agents_data = await api.get("/agents")
        
        if not agents_data:
            console.print("[red]❌ Could not fetch agents (API may be down)[/red]")
            return
        
        if not agents_data:
            console.print("[yellow]No agents currently active[/yellow]")
            return
        
        table = Table(title="🤖 Active Agents", show_header=True, header_style="bold magenta")
        table.add_column("Agent ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Status", justify="center")
        table.add_column("Capabilities", style="blue")
        table.add_column("Active Tasks", justify="right", style="yellow")
        
        for agent in agents_data:
            status_color = "green" if agent.get("status") == "active" else "red"
            capabilities = ", ".join(agent.get("capabilities", []))
            if len(capabilities) > 30:
                capabilities = capabilities[:30] + "..."
            
            table.add_row(
                agent.get("agent_id", "unknown"),
                agent.get("name", "unknown"),
                f"[{status_color}]{agent.get('status', 'unknown')}[/{status_color}]",
                capabilities,
                str(agent.get("active_tasks", 0))
            )
        
        console.print(table)
    
    asyncio.run(_list_agents())

@agents_app.command("info")
def agents_info(
    agent_id: str = typer.Argument(..., help="Agent ID to get information for")
):
    """ℹ️ Show detailed agent information"""
    async def _agents_info():
        api = ApiClient()
        
        with console.status(f"[bold blue]Fetching info for {agent_id}..."):
            agent_data = await api.get(f"/agents/{agent_id}")
        
        if not agent_data:
            console.print(f"[red]❌ Agent '{agent_id}' not found[/red]")
            return
        
        # Create detailed info panel
        info_text = f"""
[bold]Agent ID:[/bold] {agent_data.get('agent_id', 'unknown')}
[bold]Name:[/bold] {agent_data.get('name', 'unknown')}
[bold]Status:[/bold] {agent_data.get('status', 'unknown')}
[bold]Active Tasks:[/bold] {agent_data.get('active_tasks', 0)}
[bold]Memory Size:[/bold] {agent_data.get('memory_size', 0)} items
[bold]Conversation History:[/bold] {agent_data.get('conversation_history', 0)} messages
        """.strip()
        
        console.print(Panel.fit(info_text, title=f"🤖 {agent_data.get('name', 'Agent')} Details"))
        
        # Capabilities table
        capabilities = agent_data.get('capabilities', [])
        if capabilities:
            table = Table(title="🛠️ Capabilities", show_header=True, header_style="bold magenta")
            table.add_column("Name", style="cyan")
            table.add_column("Description", style="dim")
            table.add_column("Parameters", style="blue")
            
            for cap in capabilities:
                params = ", ".join(cap.get('parameters', {}).keys()) or "None"
                table.add_row(
                    cap.get('name', 'unknown'),
                    cap.get('description', 'No description'),
                    params
                )
            
            console.print(table)
    
    asyncio.run(_agents_info())

@agents_app.command("create")
def agents_create(
    agent_type: AgentType = typer.Argument(..., help="Type of agent to create"),
    agent_id: Optional[str] = typer.Option(None, "--agent-id", help="Custom agent ID")
):
    """➕ Create a new agent"""
    async def _agents_create():
        api = ApiClient()
        
        if not agent_id:
            generated_id = f"{agent_type.value}-{int(time.time())}"
        else:
            generated_id = agent_id
        
        data = {
            "agent_type": agent_type.value,
            "agent_id": generated_id
        }
        
        with console.status(f"[bold blue]Creating {agent_type.value} agent..."):
            result = await api.post("/agents", data)
        
        if result:
            console.print(f"[green]✅ Agent '{generated_id}' created successfully![/green]")
        else:
            console.print("[red]❌ Failed to create agent[/red]")
            raise typer.Exit(1)
    
    asyncio.run(_agents_create())

@agents_app.command("delete")
def agents_delete(
    agent_id: str = typer.Argument(..., help="Agent ID to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Force deletion without confirmation")
):
    """🗑️ Delete an agent"""
    async def _agents_delete():
        if not force:
            if not Confirm.ask(f"Are you sure you want to delete agent '{agent_id}'?"):
                console.print("[yellow]Deletion cancelled[/yellow]")
                return
        
        api = ApiClient()
        
        with console.status(f"[bold red]Deleting agent {agent_id}..."):
            success = await api.delete(f"/agents/{agent_id}")
        
        if success:
            console.print(f"[green]✅ Agent '{agent_id}' deleted successfully![/green]")
        else:
            console.print(f"[red]❌ Failed to delete agent '{agent_id}'[/red]")
            raise typer.Exit(1)
    
    asyncio.run(_agents_delete())

@agents_app.command("task")
def agents_task(
    agent_id: str = typer.Argument(..., help="Agent ID to send task to"),
    task_type: str = typer.Argument(..., help="Type of task to send"),
    data: Optional[str] = typer.Option(None, "-d", "--data", help="Task data as JSON string"),
    timeout: int = typer.Option(30, "--timeout", help="Task timeout in seconds")
):
    """🎯 Send a task to an agent"""
    async def _agents_task():
        api = ApiClient()
        
        task_data = {}
        if data:
            try:
                task_data = json.loads(data)
            except json.JSONDecodeError:
                console.print("[red]❌ Invalid JSON data[/red]")
                raise typer.Exit(1)
        
        # Interactive data input if not provided
        if not data:
            console.print(f"[blue]Sending '{task_type}' task to agent '{agent_id}'[/blue]")
            
            if task_type == "count_words":
                text = Prompt.ask("Enter text to analyze")
                task_data = {"text": text}
            elif task_type in ["add", "multiply"]:
                a = float(Prompt.ask("Enter first number"))
                b = float(Prompt.ask("Enter second number"))
                task_data = {"a": a, "b": b}
            elif task_type in ["echo", "uppercase"]:
                message = Prompt.ask("Enter message")
                task_data = {"message": message}
            else:
                console.print("[yellow]⚠️ Unknown task type, sending empty data[/yellow]")
        
        request_data = {
            "agent_id": agent_id,
            "task_type": task_type,
            "task_data": task_data,
            "timeout": timeout
        }
        
        with console.status("[bold blue]Sending task..."):
            result = await api.post("/tasks", request_data)
        
        if not result:
            console.print("[red]❌ Failed to send task[/red]")
            raise typer.Exit(1)
        
        task_id = result.get("task_id")
        console.print(f"[green]✅ Task submitted! ID: {task_id}[/green]")
        
        # Wait for completion and show result
        with console.status("[bold blue]Waiting for result..."):
            for _ in range(timeout):
                await asyncio.sleep(1)
                task_result = await api.get(f"/tasks/{task_id}")
                
                if task_result and task_result.get("status") in ["completed", "failed"]:
                    break
        
        if task_result:
            status = task_result.get("status")
            if status == "completed":
                result_data = task_result.get("result")
                console.print(Panel.fit(
                    f"[bold green]✅ Task Completed[/bold green]\n"
                    f"Result: {json.dumps(result_data, indent=2)}",
                    title="🎯 Task Result"
                ))
            else:
                error = task_result.get("error", "Unknown error")
                console.print(f"[red]❌ Task failed: {error}[/red]")
        else:
            console.print("[yellow]⚠️ Task status unknown or timed out[/yellow]")
    
    asyncio.run(_agents_task())

@app.command("start")
def start(
    build: bool = typer.Option(False, "--build", help="Build images before starting"),
    detach: bool = typer.Option(True, "-d", "--detach", help="Run in detached mode")
):
    """🚀 Start the entire agentic system (shortcut for docker start)"""
    docker_start(detach=detach, build=build)

@app.command("stop")
def stop(
    volumes: bool = typer.Option(False, "-v", "--volumes", help="Remove volumes as well")
):
    """🛑 Stop the entire agentic system (shortcut for docker stop)"""
    docker_stop(volumes=volumes)

@app.command("monitor")
def monitor(
    refresh: int = typer.Option(2, "-r", "--refresh", help="Refresh interval in seconds")
):
    """📊 Real-time system monitoring"""
    
    async def get_system_stats():
        api = ApiClient()
        
        # Get agents
        agents_data = await api.get("/agents") or []
        
        # Get health
        health_data = await api.get("/health") or {}
        
        # Get recent tasks
        tasks_data = await api.get("/tasks?limit=5") or {"tasks": []}
        
        return {
            "agents": agents_data,
            "health": health_data,
            "tasks": tasks_data.get("tasks", [])
        }
    
    async def _monitor():
        console.clear()
        
        with Live(console=console, refresh_per_second=1/refresh) as live:
            while True:
                try:
                    stats = await get_system_stats()
                    
                    layout = Layout()
                    layout.split_column(
                        Layout(name="header", size=3),
                        Layout(name="body"),
                        Layout(name="footer", size=3)
                    )
                    
                    layout["body"].split_row(
                        Layout(name="left"),
                        Layout(name="right")
                    )
                    
                    # Header
                    layout["header"].update(Panel.fit(
                        f"[bold blue]🤖 Agentic System Monitor[/bold blue] - {datetime.now().strftime('%H:%M:%S')}",
                        title="📊 Real-time Dashboard"
                    ))
                    
                    # Agents table
                    agents_table = Table(title="🤖 Active Agents", show_header=True)
                    agents_table.add_column("Agent", style="cyan")
                    agents_table.add_column("Status", justify="center")
                    agents_table.add_column("Tasks", justify="right")
                    
                    for agent in stats["agents"]:
                        status_color = "green" if agent.get("status") == "active" else "red"
                        agents_table.add_row(
                            agent.get("name", "unknown")[:15],
                            f"[{status_color}]●[/{status_color}]",
                            str(agent.get("active_tasks", 0))
                        )
                    
                    layout["left"].update(Panel(agents_table))
                    
                    # Recent tasks
                    tasks_table = Table(title="🎯 Recent Tasks", show_header=True)
                    tasks_table.add_column("Task ID", style="dim")
                    tasks_table.add_column("Agent", style="cyan")
                    tasks_table.add_column("Status", justify="center")
                    
                    for task in stats["tasks"][:5]:
                        task_id = task.get("task_id", "unknown")[:8] + "..."
                        agent_id = task.get("agent_id", "unknown")[:15]
                        status = task.get("status", "unknown")
                        status_color = {
                            "completed": "green",
                            "failed": "red",
                            "pending": "yellow"
                        }.get(status, "blue")
                        
                        tasks_table.add_row(
                            task_id,
                            agent_id,
                            f"[{status_color}]{status}[/{status_color}]"
                        )
                    
                    layout["right"].update(Panel(tasks_table))
                    
                    # Footer with system info
                    health_status = "🟢 Healthy" if stats["health"].get("status") == "healthy" else "🔴 Unhealthy"
                    layout["footer"].update(Panel.fit(
                        f"System Status: {health_status} | "
                        f"Active Agents: {len(stats['agents'])} | "
                        f"Press Ctrl+C to exit",
                        title="💡 System Info"
                    ))
                    
                    live.update(layout)
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    layout = Layout()
                    layout.update(Panel.fit(
                        f"[red]Error fetching data: {e}[/red]\n"
                        "Make sure the API server is running",
                        title="❌ Monitor Error"
                    ))
                    live.update(layout)
                
                await asyncio.sleep(refresh)
    
    try:
        asyncio.run(_monitor())
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitor stopped[/yellow]")

@app.command("test")
def test():
    """🧪 Run system health tests"""
    async def _test():
        console.print(Panel.fit(
            "[bold blue]🧪 Running System Health Tests[/bold blue]\n"
            "Testing API endpoints, agent communication, and service health",
            title="🔍 Health Check"
        ))
        
        api = ApiClient()
        tests_passed = 0
        total_tests = 5
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            # Test 1: API Health
            task = progress.add_task("🌐 Testing API health...", total=None)
            health_data = await api.get("/health")
            if health_data and health_data.get("status") == "healthy":
                console.print("[green]✅ API health check passed[/green]")
                tests_passed += 1
            else:
                console.print("[red]❌ API health check failed[/red]")
            progress.remove_task(task)
            
            # Test 2: Agents endpoint
            task = progress.add_task("🤖 Testing agents endpoint...", total=None)
            agents_data = await api.get("/agents")
            if agents_data is not None:
                console.print(f"[green]✅ Agents endpoint accessible ({len(agents_data)} agents)[/green]")
                tests_passed += 1
            else:
                console.print("[red]❌ Agents endpoint failed[/red]")
            progress.remove_task(task)
            
            # Test 3: MCP server
            task = progress.add_task("📡 Testing MCP server...", total=None)
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get("http://localhost:8080/health")
                    if response.status_code == 200:
                        console.print("[green]✅ MCP server accessible[/green]")
                        tests_passed += 1
                    else:
                        console.print("[red]❌ MCP server failed[/red]")
            except Exception:
                console.print("[red]❌ MCP server not reachable[/red]")
            progress.remove_task(task)
            
            # Test 4: Docker services
            task = progress.add_task("🐳 Testing Docker services...", total=None)
            docker_mgr = EarthlyManager()
            services = docker_mgr.get_service_status()
            running_services = [s for s in services if s["state"] == "running"]
            if len(running_services) >= 3:  # At least redis, postgres, api-server
                console.print(f"[green]✅ Docker services running ({len(running_services)} services)[/green]")
                tests_passed += 1
            else:
                console.print(f"[red]❌ Not enough services running ({len(running_services)} services)[/red]")
            progress.remove_task(task)
            
            # Test 5: Agent task submission
            task = progress.add_task("🎯 Testing agent task submission...", total=None)
            if agents_data and len(agents_data) > 0:
                # Try to submit a test task
                agent_id = agents_data[0].get("agent_id")
                test_task = {
                    "agent_id": agent_id,
                    "task_type": "echo",
                    "task_data": {"message": "test"}
                }
                task_result = await api.post("/tasks", test_task)
                if task_result and task_result.get("task_id"):
                    console.print("[green]✅ Task submission successful[/green]")
                    tests_passed += 1
                else:
                    console.print("[red]❌ Task submission failed[/red]")
            else:
                console.print("[yellow]⚠️ No agents available for task test[/yellow]")
            progress.remove_task(task)
        
        # Summary
        if tests_passed == total_tests:
            console.print(Panel.fit(
                f"[bold green]🎉 All tests passed! ({tests_passed}/{total_tests})[/bold green]\n"
                "Your agentic system is fully operational.",
                title="✅ Test Results"
            ))
        else:
            console.print(Panel.fit(
                f"[bold yellow]⚠️ {tests_passed}/{total_tests} tests passed[/bold yellow]\n"
                "Some components may need attention.",
                title="⚠️ Test Results"
            ))
    
    asyncio.run(_test())

@app.command("config")
def config_cmd(
    key: Optional[str] = typer.Argument(None, help="Configuration key to get/set"),
    value: Optional[str] = typer.Argument(None, help="Value to set (if provided)"),
    list_all: bool = typer.Option(False, "--list", "-l", help="List all configuration")
):
    """⚙️ Manage CLI configuration"""
    
    if list_all or (not key and not value):
        # Show all configuration
        table = Table(title="⚙️ Configuration", show_header=True, header_style="bold magenta")
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Description", style="dim")
        
        descriptions = {
            "api_url": "Base URL for the API server",
            "mcp_url": "Base URL for the MCP server", 
            "timeout": "Request timeout in seconds",
            "auto_start": "Auto-start services on CLI launch",
            "preferred_editor": "Preferred text editor",
            "log_level": "Default log level"
        }
        
        for k, v in config.config.items():
            table.add_row(k, str(v), descriptions.get(k, ""))
        
        console.print(table)
        
        console.print(f"\n[dim]Config file: {config.config_file}[/dim]")
        
    elif key and value:
        # Set configuration
        old_value = config.get(key)
        config.set(key, value)
        console.print(f"[green]✅ Set {key}: {old_value} → {value}[/green]")
        
    elif key:
        # Get configuration
        value = config.get(key)
        if value is not None:
            console.print(f"[cyan]{key}[/cyan]: [green]{value}[/green]")
        else:
            console.print(f"[red]❌ Configuration key '{key}' not found[/red]")
            raise typer.Exit(1)

@app.command("logs")
def logs_cmd(
    service: Optional[str] = typer.Argument(None, help="Service to view logs for"),
    follow: bool = typer.Option(False, "-f", "--follow", help="Follow log output"),
    tail: int = typer.Option(100, "--tail", help="Number of lines to show"),
    level: LogLevel = typer.Option(LogLevel.INFO, "--level", help="Minimum log level to show")
):
    """📋 View system logs (shortcut for docker logs)"""
    docker_logs(service=service, follow=follow, tail=tail)

@app.command("shell")
def shell(
    service: str = typer.Argument("api-server", help="Service to open shell in")
):
    """🐚 Open interactive shell in a service container"""
    docker_mgr = EarthlyManager()
    
    if not docker_mgr.check_docker_compose():
        console.print("[red]❌ docker-compose is not available[/red]")
        raise typer.Exit(1)
    
    console.print(f"[blue]🐚 Opening shell in {service}...[/blue]")
    
    try:
        docker_mgr.open_shell(service)
    except KeyboardInterrupt:
        console.print("\n[yellow]Shell session ended[/yellow]")

@app.command("ps")
def ps():
    """📊 Show running processes (shortcut for docker status)"""
    docker_status()

@app.command("restart")
def restart(
    service: Optional[str] = typer.Argument(None, help="Service to restart (all if not specified)")
):
    """🔄 Restart services (shortcut for docker restart)"""
    docker_restart(service=service)

@app.command("clean")
def clean(
    all_data: bool = typer.Option(False, "--all", help="Remove all data including volumes"),
    force: bool = typer.Option(False, "--force", "-f", help="Force cleanup without confirmation")
):
    """🧹 Clean up Docker resources"""
    
    if not force:
        if all_data:
            if not Confirm.ask("⚠️ This will remove ALL data including volumes. Continue?"):
                console.print("[yellow]Cleanup cancelled[/yellow]")
                return
        else:
            if not Confirm.ask("Clean up stopped containers and unused images?"):
                console.print("[yellow]Cleanup cancelled[/yellow]")
                return
    
    docker_mgr = EarthlyManager()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        # Stop services
        task = progress.add_task("🛑 Stopping services...", total=None)
        if all_data:
            docker_mgr.run_compose_command(["down", "--volumes", "--remove-orphans"], use_earthly_compose=True)
        else:
            docker_mgr.run_compose_command(["down", "--remove-orphans"], use_earthly_compose=True)
        progress.remove_task(task)
        
        # Clean Docker system
        task = progress.add_task("🧹 Cleaning Docker system...", total=None)
        subprocess.run(["docker", "system", "prune", "-f"], capture_output=True)
        progress.remove_task(task)
        
        if all_data:
            task = progress.add_task("🗑️ Removing volumes and images...", total=None)
            subprocess.run(["docker", "volume", "prune", "-f"], capture_output=True)
            subprocess.run(["docker", "image", "prune", "-a", "-f"], capture_output=True)
            progress.remove_task(task)
    
    console.print("[green]✅ Cleanup completed![/green]")

@app.command("update")
def update():
    """🔄 Update the agentic system"""
    console.print(Panel.fit(
        "[bold blue]🔄 Updating Agentic System[/bold blue]\n"
        "This will pull latest changes and rebuild images",
        title="📦 System Update"
    ))
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        # Pull latest code (if in git repo)
        task = progress.add_task("📥 Pulling latest changes...", total=None)
        try:
            subprocess.run(["git", "pull"], capture_output=True, check=True)
            console.print("[green]✅ Code updated[/green]")
        except (subprocess.CalledProcessError, FileNotFoundError):
            console.print("[yellow]⚠️ Not a git repository or no updates available[/yellow]")
        progress.remove_task(task)
        
        # Rebuild images
        task = progress.add_task("🔨 Rebuilding images...", total=None)
        docker_mgr = EarthlyManager()
        result = docker_mgr.run_earthly_command(["+all", "--no-cache"])
        if result.returncode == 0:
            console.print("[green]✅ Images rebuilt[/green]")
        else:
            console.print("[red]❌ Failed to rebuild images[/red]")
        progress.remove_task(task)
        
        # Restart services
        task = progress.add_task("🚀 Restarting services...", total=None)
        docker_mgr.restart_services()
        progress.remove_task(task)
    
    console.print("[green]✅ Update completed![/green]")

if __name__ == "__main__":
    app()