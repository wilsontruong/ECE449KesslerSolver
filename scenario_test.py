import time
from kesslergame import Scenario, KesslerGame, GraphicsType, TrainerEnvironment
from test_controller import TestController
from scott_dick_controller import ScottDickController
from graphics_both import GraphicsBoth
from group_controller import GroupController

my_test_scenario = Scenario(name='Test Scenario',
                            num_asteroids=5,
                            ship_states=[
                                {'position': (400, 400), 'angle': 90, 'lives': 3, 'team': 1},
                                {'position': (600, 400), 'angle': 90, 'lives': 3, 'team': 2},
                            ],
                            map_size=(1000, 800),
                            time_limit=60,
                            ammo_limit_multiplier=0,
                            stop_if_no_ammo=False)

game_settings = {'perf_tracker': True,
                 'graphics_type': GraphicsType.Tkinter,
                 'realtime_multiplier': 1,
                 'graphics_obj': None}
game = KesslerGame(settings=game_settings) # Use this to visualize the game scenario GRAPHICS
# game = TrainerEnvironment(settings=game_settings) # Use this for max-speed, no-graphics simulation WITHOUT GRAPHICS
pre = time.perf_counter()
score, perf_data = game.run(scenario=my_test_scenario, controllers = [TestController(), GroupController()])
print('Scenario eval time: '+str(time.perf_counter()-pre))
print(score.stop_reason)
print('Asteroids hit: ' + str([team.asteroids_hit for team in score.teams]))
print('Deaths: ' + str([team.deaths for team in score.teams]))
print('Accuracy: ' + str([team.accuracy for team in score.teams]))
print('Mean eval time: ' + str([team.mean_eval_time for team in score.teams]))
print('Evaluated frames: ' + str([controller.eval_frames for controller in score.final_controllers]))
