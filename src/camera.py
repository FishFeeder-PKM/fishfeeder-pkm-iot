import re
import asyncio
import socketio
import cv2
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate, VideoStreamTrack
from aiortc.contrib.media import MediaStreamTrack, VideoFrame
from datetime import datetime
import queue
import threading
from dotenv import load_dotenv
import os

# Load environment variables from the .env file
load_dotenv(f"{os.path.dirname(os.path.abspath(__file__))}/../.env")

SIGNALING_SERVER_URL = os.getenv("SIGNALING_SERVER_URL")
DEVICE_ID = os.getenv("DEVICE_ID")
ENABLE_LOGGING = bool(os.getenv("CONFIG_ENABLE_LOGGING"))

# WebSocket client to connect to Node.js signaling server
sio = socketio.AsyncClient()

# Network state
peer_connections = {} # Store peer connections

# Shared webcam state
webcam = None

# Connect to signaling server
@sio.event
async def connect():
    logger("Network", "Connected to signaling server!")
    await sio.emit("join-room", { "roomId": DEVICE_ID })

@sio.event
async def disconnect():
    # global peer_connections
    logger("Network", "Disconnected from signaling server!")
    # peer_connections.clear()
    stop_webcam()

# Function to start the webcam
def start_webcam():
    global webcam
    # Initialize the webcam
    webcam = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not webcam.isOpened():
        logger("Hardware", "Failed to open the webcam", level="ERROR")
        return
    
    logger("Hardware", "Webcam turned on.")

def start_video_stream(pc: RTCPeerConnection):
    # Start capturing video
    logger("Network", f"Video stream turned on for sid '{pc.sid}'")
    video_track = WebcamCapture()
    video_track.start()
    pc.addTrack(video_track)
    return pc

# Function to stop the webcam
def stop_webcam():
    global webcam
    if bool(webcam) and webcam.isOpened():
        webcam.release()
        logger("Hardware", "Webcam turned off")   

def update_peer_connections(pc: RTCPeerConnection):
    peer_connections[pc.sid] = pc

# Handle ICE connection state change
async def on_ice_connection_state_change(pc: RTCPeerConnection):
    # peer_connections[sid] = pc
    update_peer_connections(pc)
    state = pc.iceConnectionState
    logger("Network", f"ICE Connection State: {state}")

    if state == "checking":
        logger("Network", "ICE is in 'checking' state...")
        
        # Start a timeout for 10 seconds if it's the first time entering the "checking" state
        if pc.timeout is None:
            pc.timeout = asyncio.create_task(check_ice_timeout(pc))
    
    elif state == "completed":
        logger("Network", "ICE connection established!")
        # If the connection is successful, cancel the timeout task
        if pc.timeout:
            pc.timeout.cancel()
            pc.timeout = None
            pc.is_completed = True
            update_peer_connections(pc)
    
    elif state in ["disconnected", "failed", "closed"]:
        await close_peer_connection(pc, pc.is_completed)

# Timeout function to handle 'checking' state
async def check_ice_timeout(pc: RTCPeerConnection):
    try:
        # Wait for the connection to be established or completed
        await asyncio.sleep(5) # seconds
        
        # If still in 'checking' state after 10 seconds, mark it as 'disconnected'
        if pc.iceConnectionState == "checking":
            logger("Network", f"ICE connection took too long for sid '{pc.sid}', closing peer connection...")
            await close_peer_connection(pc, has_stream=False)
    except asyncio.CancelledError:
        # If the task was cancelled (i.e., connection successful), ignore the error
        pass    

# Closes peer connection
async def close_peer_connection(pc: RTCPeerConnection, has_stream=True):
    global peer_connections, video_track

    sid = pc.sid
    if peer_connections[sid]:
        del peer_connections[sid]
    await pc.close()
    logger("Network", f"Peer connection closed for sid '{sid}'")

    # Stop webcam if there is no active connections
    if not bool(peer_connections):
        logger("Hardware", "No active connections, CLOSING WEBCAM...")
        stop_webcam()

# Receive offer from the client (HTML client) via signaling server
@sio.on("offer")
async def handle_offer(offer, sid):
    logger("Network", f"Received offer from sid '{sid}'!")

    # Create the peer connection
    pc = RTCPeerConnection()
    pc.sid = sid
    pc.timeout = None
    pc.is_completed = False

    # Set up ICE connection state change listener
    pc.on("iceconnectionstatechange", lambda: asyncio.create_task(on_ice_connection_state_change(pc)))

    try:
        # Only open the webcam if there is atleast an active connection
        if not bool(peer_connections):
            start_webcam()
        
        # Add track to peer connection
        pc = start_video_stream(pc)

        # Update peer connection
        update_peer_connections(pc)

        # Set remote description (offer)
        await pc.setRemoteDescription(RTCSessionDescription(
            sdp=offer["sdp"],
            type=offer["type"],
        ))

        # Create answer and send it back to client
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        # Update peer connection
        update_peer_connections(pc)

        await sio.emit("answer", {
            "roomId": DEVICE_ID,
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type,
        })

        logger("Network", f"Sent answer to sid '{sid}'!")

    except Exception as e:
        logger("Network", f"Error handling offer: {e}", level="ERROR")

def parse_candidate(candidate_str):
    # Regular expression to parse the candidate string
    pattern = r"candidate:(?P<foundation>\d+) (?P<component>\d) (?P<protocol>\w+) (?P<priority>\d+) (?P<ip>\S+) (?P<port>\d+) typ (?P<type>\w+)"

    # Try to match the candidate string against the pattern
    match = re.match(pattern, candidate_str)
    if match:
        return match.groupdict()
    else:
        raise ValueError("Invalid candidate string format")

def create_ice_candidate(candidate_data, sdp_mid, sdp_mline_index):
    return RTCIceCandidate(
        foundation=candidate_data["foundation"],
        component=int(candidate_data["component"]),
        protocol=candidate_data["protocol"],
        priority=int(candidate_data["priority"]),
        ip=candidate_data["ip"],
        port=int(candidate_data["port"]),
        type=candidate_data["type"],
        sdpMid=sdp_mid,
        sdpMLineIndex=sdp_mline_index,
    )

# Receive ICE candidate from the client
@sio.on("candidate")
async def handle_candidate(candidate, sid):
    global peer_connections

    # Check if the peer connection exists for the given sid
    if sid in peer_connections:
        try:
            # Parse the candidate string
            candidate_data = parse_candidate(candidate["candidate"])

            # Extract sdpMid and sdpMLineIndex
            sdp_mid = candidate.get("sdpMid", "")
            sdp_mline_index = candidate["sdpMLineIndex"]

            # Create RTCIceCandidate instance from the received data
            ice_candidate = create_ice_candidate(candidate_data, sdp_mid, sdp_mline_index)
            
            await peer_connections[sid].addIceCandidate(ice_candidate)

            logger("Network", f"Added ICE candidate: {candidate['candidate']}")

        except Exception as e:
            logger(f"Network", f"Error adding ICE candidate: {e}", level="ERROR")
    else:
        logger("Network", f"No active peer connection for SID: {sid}.", level="ERROR")

# Camera Capturing class
class WebcamCapture(VideoStreamTrack):
    """
    A custom video stream track for capturing the user's screen.
    """
    def __init__(self) -> None:
        global webcam
        super().__init__()
        self.queue = queue.Queue(10)
        # Open the default camera (camera index 0)
        if not webcam.isOpened():
            raise RuntimeError("Could not open webcam")

    async def recv(self):
        """
        Asynchronously receives frames from the webcam capture.
        """
        frame = await asyncio.to_thread(self.queue.get)

        video_frame = VideoFrame.from_ndarray(frame, format="bgr24")

        # Set timestamp for the frame
        pts, time_base = await self.next_timestamp()
        video_frame.pts = pts
        video_frame.time_base = time_base

        return video_frame

    def capture_frame(self):
        """
        Capture frames from the webcam, put them into the queue.
        This method is intended to run in a separate thread.
        """
        global webcam
        while True:
            # with camera_lock:
            success, frame = webcam.read()
            if success:
                self.queue.put(frame)
            else:
                logger("Hardware", "Failed to capture frame from camera!", level="WARN")
                break;

    def start(self):
        """
        Start the camera capture in a separate thread.
        """
        self.is_started = True
        logger("Hardware", "Video track started!")
        capture_thread = threading.Thread(target=self.capture_frame, daemon=True)
        capture_thread.start()

def logger(category, message, level="INFO"):
    if ENABLE_LOGGING:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}]: {category}: {message}")

# Set up connection and stream
async def run():
    try:
        # Connect to signaling server
        await sio.connect(SIGNALING_SERVER_URL, transports=["websocket"])
        logger("Network", "Waiting for signaling server connection...")

        # Keep the connection open and wait for events (offer, candidate)
        await sio.wait()

    except Exception as e:
        logger("Network", f"Error connecting to server: {e}", level="ERROR")

if __name__ == "__main__":
    asyncio.run(run())
