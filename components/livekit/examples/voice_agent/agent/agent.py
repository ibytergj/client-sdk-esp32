import json
import logging
import os
from enum import Enum
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import (
    AgentSession,
    Agent,
    inference,
    RunContext,
    RoomInputOptions,
    function_tool,
    get_job_context,
    ToolError,
)
from livekit.plugins import (
    openai,
    noise_cancellation,
)

# If enabled, RPC calls will not be performed.
TEST_MODE = False

load_dotenv()

class LEDColor(str, Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"
    WHITE = "white"

class Assistant(Agent):
    def __init__(self, board_info: dict, participant_identity: str) -> None:
        self._participant_identity = participant_identity
        exposed_controls = board_info.get("exposed_controls", [])
        if "RGB LED" in exposed_controls:
            led_guidance = (
                "The board has one RGB pixel. Setting a color replaces its "
                "previous color, and turning it off clears that pixel. "
                "To turn on or change its color, call set_led_state exactly once "
                "with the requested color and state=true. Never send state=false "
                "for other colors: those calls turn off the entire pixel. "
                "Leave the pixel on until the user explicitly requests off. "
                "For an off request, call set_led_state exactly once with "
                "state=false. Do not blink or cycle colors unless requested."
            )
        elif "red LED" in exposed_controls or "blue LED" in exposed_controls:
            led_guidance = (
                "The board exposes independent red and blue LEDs; green and "
                "white are unsupported."
            )
        else:
            led_guidance = "This example exposes no LED control on this board."
        super().__init__(
            instructions=f"""You are a helpful voice AI assistant connected to this hardware:
            {json.dumps(board_info)}
            Answer questions using only these reported capabilities. Distinguish hardware that is physically
            present from controls exposed by this LiveKit example. Never claim that an unexposed peripheral can
            be controlled. {led_guidance} You cannot read the current LED state. No markdown is allowed in your
            responses.
            """
        )

    @function_tool()
    async def set_led_state(self, _: RunContext, led: LEDColor, state: bool) -> None:
        """Set the state of an on-board LED.

        Args:
            led: Which LED to set. S3 supports red and blue only; S31 RGB
                boards also support green and white.
            state: The state to set the LED to (i.e. on or off).
        """
        if TEST_MODE: return
        try:
            room = get_job_context().room
            await room.local_participant.perform_rpc(
                destination_identity=self._participant_identity,
                method="set_led_state",
                payload=json.dumps({ "color": led.value, "state": state })
            )
        except Exception:
            raise ToolError("Unable to set LED state")

    @function_tool()
    async def get_cpu_temp(self, _: RunContext) -> float:
        """Get the current temperature of the CPU.

        Returns:
            The temperature reading in degrees Celsius.
        """
        if TEST_MODE: return 25.0
        try:
            room = get_job_context().room
            response = await room.local_participant.perform_rpc(
                destination_identity=self._participant_identity,
                method="get_cpu_temp",
                response_timeout=10,
                payload=""
            )
            if isinstance(response, str):
                try:
                    response = float(response)
                except ValueError:
                    raise ToolError("Received invalid temperature value")
            return response
        except Exception:
            raise ToolError("Unable to retrieve CPU temperature")

async def get_board_info(ctx: agents.JobContext, participant_identity: str) -> dict:
    try:
        response = await ctx.room.local_participant.perform_rpc(
            destination_identity=participant_identity,
            method="get_board_info",
            response_timeout=10,
            payload="",
        )
        if isinstance(response, str):
            info = json.loads(response)
            if isinstance(info, dict):
                return info
    except Exception:
        pass
    return {
        "board": "ESP32-S3-Korvo-2 or firmware without board discovery",
        "led": "independent red and blue indicator LEDs",
        "exposed_controls": ["red LED", "blue LED", "CPU temperature"],
    }


def create_session():
    backend = os.getenv("LIVEKIT_AGENT_BACKEND", "openai-realtime")
    if backend == "livekit-inference":
        # Use the project's LiveKit credentials for all three model services.
        # STT endpointing avoids requiring a separate local VAD model.
        return AgentSession(
            stt=inference.STT(
                "deepgram/nova-3", language="en",
                extra_kwargs={"endpointing": 500},
            ),
            llm=inference.LLM("openai/gpt-4.1-mini"),
            tts=inference.TTS(
                "cartesia/sonic-3",
                voice=os.getenv(
                    "LIVEKIT_AGENT_VOICE_ID",
                    "9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
                ),
            ),
            turn_detection="stt",
            min_endpointing_delay=1.2,
            allow_interruptions=False,
        )
    if backend != "openai-realtime":
        raise ValueError("LIVEKIT_AGENT_BACKEND must be livekit-inference or openai-realtime")
    return AgentSession(
        llm=openai.realtime.RealtimeModel(
            voice="echo",
            model="gpt-4o-mini-realtime-preview-2024-12-17",
        )
    )


async def entrypoint(ctx: agents.JobContext):
    session = create_session()
    await ctx.connect()
    participant = await ctx.wait_for_participant()
    board_info = await get_board_info(ctx, participant.identity)
    logging.getLogger("esp32-agent").info("Detected board: %s", board_info.get("board"))
    await session.start(
        room=ctx.room,
        agent=Assistant(board_info, participant.identity),
        room_input_options=RoomInputOptions(
            participant_identity=participant.identity,
            noise_cancellation=noise_cancellation.BVC()
        )
    )
    logging.getLogger("esp32-agent").info("Voice session ready")
if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
