"""
AgentK — SDK Bootstrap Entry Point
===================================
Bootstraps the AgentK self-evolving agent system through the google-antigravity SDK.
The SDK manages lifecycle, crash resilience, and the interactive loop.
The user is the presence — the system operates independently.
"""

import sys
import os
import signal
import atexit

# ---------------------------------------------------------------------------
# Crash resilience: Prevent recursive fatal error (SIGABRT) when the parent
# process exits before this child finishes, causing a broken stdout pipe.
# See: https://docs.python.org/3/library/signal.html#note-on-sigpipe
# ---------------------------------------------------------------------------
signal.signal(signal.SIGPIPE, signal.SIG_DFL)


def _flush_streams_safely():
    """Safely flush stdout/stderr at exit, redirecting to devnull on broken pipe."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except (BrokenPipeError, OSError):
            try:
                devnull = os.open(os.devnull, os.O_WRONLY)
                os.dup2(devnull, stream.fileno())
                os.close(devnull)
            except (OSError, ValueError):
                pass


atexit.register(_flush_streams_safely)

# ---------------------------------------------------------------------------
# Environment & path setup
# ---------------------------------------------------------------------------
AGENTK_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(AGENTK_ROOT)
if AGENTK_ROOT not in sys.path:
    sys.path.insert(0, AGENTK_ROOT)

from dotenv import load_dotenv
load_dotenv()

# ---------------------------------------------------------------------------
# SDK Bootstrap
# ---------------------------------------------------------------------------
import asyncio
from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig
from google.antigravity.utils.interactive import run_interactive_loop

# Import the bridge that connects the SDK to existing LangGraph agents
sys.path.insert(0, os.path.join(AGENTK_ROOT, "agents"))
from sdk_bridge import get_system_prompt


async def main():
    """
    Bootstrap AgentK through the Antigravity SDK.
    The SDK becomes the outer shell — the bootloader — that manages lifecycle,
    crash resilience, and the interactive loop. Existing LangGraph agents
    (hermes, agent_smith, tool_maker, software_engineer, web_researcher)
    remain the inner kernel, callable through the bridge layer.
    """
    system_prompt = get_system_prompt()

    from sovereign_gate import get_sovereign_policies
    policies = get_sovereign_policies()

    config = LocalAgentConfig(
        system_instructions=system_prompt,
        capabilities=CapabilitiesConfig(),
        policies=policies,
    )

    print("=" * 60)
    print("  AgentK — Self-Evolving AGI System")
    print("  Bootstrapped via Antigravity SDK")
    print("=" * 60)
    print()

    async with Agent(config) as agent:
        await run_interactive_loop(agent)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nAgentK session ended.")
    except Exception as e:
        print(f"\n[AgentK] Fatal error: {e}", file=sys.stderr)
        sys.exit(1)