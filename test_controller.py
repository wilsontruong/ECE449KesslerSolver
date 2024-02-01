from kesslergame import KesslerController
from typing import Dict, Tuple
import skfuzzy as fuzz
class TestController(KesslerController):
    def __init__(self):
        self.eval_frames = 0

    def actions(self, ship_state: Dict, game_state: Dict) -> Tuple[float, float, bool]:
        """
        Method processed each time step by this controller.
        """
        thrust = 0
        turn_rate = 90
        fire = True
        self.eval_frames +=1
        return thrust, turn_rate, fire
    
    @property
    def name(self) -> str:
        return "Test Controller"
