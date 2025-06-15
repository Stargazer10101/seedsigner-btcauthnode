import time
from dataclasses import dataclass
from gettext import gettext as _
from PIL import Image

import os
from seedsigner.gui.components import GUIConstants, Fonts
from seedsigner.gui import renderer
from seedsigner.gui.screens.screen import BaseScreen
from seedsigner.gui.screens.scan_screens import BaseThread
from seedsigner.hardware.camera import Camera
from seedsigner.models.settings import Settings
from seedsigner.models.singleton import Singleton


PHOTO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "photos")
if not os.path.exists(PHOTO_DIR):
    os.makedirs(PHOTO_DIR)


@dataclass
class PhotoCaptureScreen(BaseScreen):
    """
    Live preview screen for photo capture
    """
    instructions_text: str = None
    resolution: tuple[int,int] = (720, 480)  # Higher resolution for photos
    framerate: int = 12
    render_rect: tuple[int,int,int,int] = None

    def __post_init__(self):
        from seedsigner.hardware.camera import Camera
        super().__post_init__()
        
        self.instructions_text = "< " + _("back") + "  |  " + _(self.instructions_text)
        self.camera = Camera.get_instance()
        self.camera.start_single_frame_mode(resolution=self.resolution)
        
        self.threads.append(PhotoCaptureScreen.LivePreviewThread(
            renderer=self.renderer,
            instructions_text=self.instructions_text,
            render_rect=self.render_rect
        ))

    class LivePreviewThread(BaseThread):
        def __init__(self, renderer: renderer.Renderer, instructions_text: str, render_rect: tuple[int,int,int,int]):
            self.camera = Camera.get_instance()
            self.renderer = renderer
            self.instructions_text = instructions_text
            if render_rect:
                self.render_rect = render_rect            
            else:
                self.render_rect = (0, 0, self.renderer.canvas_width, self.renderer.canvas_height)
            self.render_width = self.render_rect[2] - self.render_rect[0]
            self.render_height = self.render_rect[3] - self.render_rect[1]
            
            super().__init__()

        def run(self):
            while True:
                if self.stopped():
                    break

                # Capture frame
                frame = self.camera.capture_frame()
                
                # Convert to RGB for display
                frame = frame.convert('RGB')
                
                # Resize to fit screen
                frame = frame.resize((self.render_width, self.render_height))
                
                # Draw frame
                self.renderer.draw_image(frame, self.render_rect)
                
                # Draw instructions
                self.renderer.draw_text(
                    text=self.instructions_text,
                    font=Fonts.get_font(GUIConstants.BODY_FONT_NAME, GUIConstants.BODY_FONT_SIZE),
                    pos=(GUIConstants.EDGE_PADDING, GUIConstants.EDGE_PADDING),
                    background_color=GUIConstants.BACKGROUND_COLOR,
                )
                
                # Check for button press
                if self.controller.buttons.check_for_low(button=ButtonOption.RIGHT):
                    try:
                        # Capture photo
                        timestamp = time.strftime("%Y%m%d_%H%M%S")
                        photo_path = os.path.join(PHOTO_DIR, f"photo_{timestamp}.jpg")
                        print(f"Attempting to save photo to: {photo_path}")  # Debug print
                        
                        # Save the current frame
                        frame.save(photo_path)
                        
                        # Show confirmation
                        self.renderer.draw_text(
                            text=f"Photo saved to:\n{os.path.basename(photo_path)}",
                            font=Fonts.get_font(GUIConstants.BODY_FONT_NAME, GUIConstants.BODY_FONT_SIZE),
                            pos=(GUIConstants.EDGE_PADDING, self.render_height - GUIConstants.EDGE_PADDING - 3*GUIConstants.BODY_FONT_SIZE),
                            background_color=GUIConstants.BACKGROUND_COLOR,
                        )
                        self.renderer.show_image()
                        time.sleep(3)  # Show confirmation for 3 seconds
                        
                        # Stop the thread
                        self.stop()
                        
                    except Exception as e:
                        print(f"Error saving photo: {str(e)}")  # Debug print
                        self.renderer.draw_text(
                            text="Error saving photo",
                            font=Fonts.get_font(GUIConstants.BODY_FONT_NAME, GUIConstants.BODY_FONT_SIZE),
                            pos=(GUIConstants.EDGE_PADDING, self.render_height - GUIConstants.EDGE_PADDING - 3*GUIConstants.BODY_FONT_SIZE),
                            background_color=GUIConstants.BACKGROUND_COLOR,
                        )
                        self.renderer.show_image()
                        time.sleep(3)  # Show error message for 3 seconds
                        self.stop()

    def on_exit(self):
        self.camera.stop_single_frame_mode()
