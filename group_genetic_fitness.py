import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import EasyGA
import os
import random
import time
from kesslergame import Scenario, KesslerGame, GraphicsType, TrainerEnvironment
from test_controller import TestController
from scott_dick_controller import ScottDickController
from graphics_both import GraphicsBoth
from group_controller import GroupController

from kesslergame import KesslerController # In Eclipse, the name of the library is kesslergame, not src.kesslergame
from typing import Dict, Tuple
from cmath import sqrt
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import math
import numpy as np
import matplotlib as plt
import math



class GroupControllerGA(KesslerController):
    def __init__(self, thrustValues):
        print("thrustValues:", thrustValues)

        self.eval_frames = 0 #What is this?
        # self.targeting_control is the targeting rulebase, which is static in this controller.
        # Declare variables
        bullet_time = ctrl.Antecedent(np.arange(0,1.0,0.002), 'bullet_time')
        theta_delta = ctrl.Antecedent(np.arange(-1*math.pi,math.pi,0.1), 'theta_delta') # Radians due to Python
        ship_turn = ctrl.Consequent(np.arange(-180,180,1), 'ship_turn') # Degrees due to Kessler
        ship_fire = ctrl.Consequent(np.arange(-1,1,0.1), 'ship_fire')
        asteroid_front = ctrl.Antecedent(np.arange(0, 1000, 1), 'asteroid_front') # 0: No asteroid, 1: Asteroid present
        asteroid_back = ctrl.Antecedent(np.arange(0, 1000, 1), 'asteroid_back') # 0: No asteroid, 1: Asteroid present
        ship_thrust = ctrl.Consequent(np.arange(-480, 480, 1), 'ship_thrust')

        #Declare fuzzy sets for bullet_time (how long it takes for the bullet to reach the intercept point)
        bullet_time['S'] = fuzz.trimf(bullet_time.universe,[0,0,0.05])
        bullet_time['M'] = fuzz.trimf(bullet_time.universe, [0,0.05,0.1])
        bullet_time['L'] = fuzz.smf(bullet_time.universe,0.0,0.1)

        #Declare fuzzy sets for theta_delta (degrees of turn needed to reach the calculated firing angle)
        theta_delta['NL'] = fuzz.zmf(theta_delta.universe, -1*math.pi/3,-1*math.pi/6)
        theta_delta['NS'] = fuzz.trimf(theta_delta.universe, [-1*math.pi/3,-1*math.pi/6,0])
        theta_delta['Z'] = fuzz.trimf(theta_delta.universe, [-1*math.pi/6,0,math.pi/6])
        theta_delta['PS'] = fuzz.trimf(theta_delta.universe, [0,math.pi/6,math.pi/3])
        theta_delta['PL'] = fuzz.smf(theta_delta.universe,math.pi/6,math.pi/3)

        #Declare fuzzy sets for the ship_turn consequent; this will be returned as turn_rate.
        ship_turn['NL'] = fuzz.trimf(ship_turn.universe, [-180,-180,-30])
        ship_turn['NS'] = fuzz.trimf(ship_turn.universe, [-90,-30,0])
        ship_turn['Z'] = fuzz.trimf(ship_turn.universe, [-30,0,30])
        ship_turn['PS'] = fuzz.trimf(ship_turn.universe, [0,30,90])
        ship_turn['PL'] = fuzz.trimf(ship_turn.universe, [30,180,180])

        #Declare singleton fuzzy sets for the ship_fire consequent; -1 -> don't fire, +1 -> fire; this will be  thresholded
        #   and returned as the boolean 'fire'
        ship_fire['N'] = fuzz.trimf(ship_fire.universe, [-1,-1,0.0])
        ship_fire['Y'] = fuzz.trimf(ship_fire.universe, [0.0,1,1])

        # Fuzzy sets for asteroid_front
        asteroid_front['ReallyClose'] = fuzz.trimf(asteroid_front.universe, [0, 0, 150])      # Really Close: 0 to 50 units
        asteroid_front['Close'] = fuzz.trimf(asteroid_front.universe, [100, 200, 300])         # Close: 40 to 100 units
        asteroid_front['Medium'] = fuzz.trimf(asteroid_front.universe, [250, 400, 500])      # Neutral: 80 to 150 units
        asteroid_front['Far'] = fuzz.trimf(asteroid_front.universe, [450, 600, 700])         # Far: 140 to 200 units
        asteroid_front['ReallyFar'] = fuzz.trimf(asteroid_front.universe, [650, 800, 1000]) # Really Far: 175 to 250 units

        # Fuzzy sets for asteroid_back
        asteroid_back['ReallyClose'] = fuzz.trimf(asteroid_back.universe, [0, 0, 150])       # Really Close: 0 to 50 units
        asteroid_back['Close'] = fuzz.trimf(asteroid_back.universe, [100, 200, 300])           # Close: 40 to 100 units
        asteroid_back['Medium'] = fuzz.trimf(asteroid_back.universe, [250, 400, 500])        # Neutral: 80 to 150 units
        asteroid_back['Far'] = fuzz.trimf(asteroid_back.universe, [450, 600, 700])           # Far: 140 to 200 units
        asteroid_back['ReallyFar'] = fuzz.trimf(asteroid_back.universe, [650, 800, 1000])  # Really Far: 175 to 250 units

        # Declare fuzzy sets for the ship thrust (HHow hard or long it will turn on the thrusters)
        ship_thrust['BackwardStrong'] = fuzz.trimf(ship_thrust.universe, [thrustValues[0], thrustValues[1], thrustValues[2]]) # Backwards strong
        ship_thrust['BackwardWeak'] = fuzz.trimf(ship_thrust.universe, [thrustValues[3], thrustValues[4], thrustValues[5]]) # Backwards Weak
        ship_thrust['Neutral'] = fuzz.trimf(ship_thrust.universe, [thrustValues[6], thrustValues[7], thrustValues[8]]) # Neutral (Don't move)
        ship_thrust['ForwardWeak'] = fuzz.trimf(ship_thrust.universe, [thrustValues[9], thrustValues[10], thrustValues[11]]) # Forward Weak
        ship_thrust['ForwardStrong'] = fuzz.trimf(ship_thrust.universe, [thrustValues[12], thrustValues[13], thrustValues[14]]) # Forward Strong

        #Declare each fuzzy rule
        rule1 = ctrl.Rule(bullet_time['L'] & theta_delta['NL'], (ship_turn['NL'], ship_fire['N']))
        rule2 = ctrl.Rule(bullet_time['L'] & theta_delta['NS'], (ship_turn['NS'], ship_fire['Y']))
        rule3 = ctrl.Rule(bullet_time['L'] & theta_delta['Z'], (ship_turn['Z'], ship_fire['Y']))
        rule4 = ctrl.Rule(bullet_time['L'] & theta_delta['PS'], (ship_turn['PS'], ship_fire['Y']))
        rule5 = ctrl.Rule(bullet_time['L'] & theta_delta['PL'], (ship_turn['PL'], ship_fire['N']))
        rule6 = ctrl.Rule(bullet_time['M'] & theta_delta['NL'], (ship_turn['NL'], ship_fire['N']))
        rule7 = ctrl.Rule(bullet_time['M'] & theta_delta['NS'], (ship_turn['NS'], ship_fire['Y']))
        rule8 = ctrl.Rule(bullet_time['M'] & theta_delta['Z'], (ship_turn['Z'], ship_fire['Y']))
        rule9 = ctrl.Rule(bullet_time['M'] & theta_delta['PS'], (ship_turn['PS'], ship_fire['Y']))
        rule10 = ctrl.Rule(bullet_time['M'] & theta_delta['PL'], (ship_turn['PL'], ship_fire['N']))
        rule11 = ctrl.Rule(bullet_time['S'] & theta_delta['NL'], (ship_turn['NL'], ship_fire['Y']))
        rule12 = ctrl.Rule(bullet_time['S'] & theta_delta['NS'], (ship_turn['NS'], ship_fire['Y']))
        rule13 = ctrl.Rule(bullet_time['S'] & theta_delta['Z'], (ship_turn['Z'], ship_fire['Y']))
        rule14 = ctrl.Rule(bullet_time['S'] & theta_delta['PS'], (ship_turn['PS'], ship_fire['Y']))
        rule15 = ctrl.Rule(bullet_time['S'] & theta_delta['PL'], (ship_turn['PL'], ship_fire['Y']))

        rule16 = ctrl.Rule(asteroid_front['ReallyClose'] | asteroid_back['ReallyClose'], ship_thrust['Neutral'])
        rule17 = ctrl.Rule(asteroid_front['Close'] | asteroid_back['Close'], ship_thrust['Neutral'])
        rule18 = ctrl.Rule(asteroid_front['Medium'] | asteroid_back['Medium'], ship_thrust['Neutral'])
        rule19 = ctrl.Rule(asteroid_front['Far'] | asteroid_back['Far'], ship_thrust['Neutral'])
        rule20 = ctrl.Rule(asteroid_front['ReallyFar'] | asteroid_back['ReallyFar'], ship_thrust['Neutral'])

        rule21 = ctrl.Rule(asteroid_front['ReallyClose'] | asteroid_back['Medium'], ship_thrust['BackwardWeak'])
        rule22 = ctrl.Rule(asteroid_front['ReallyClose'] | asteroid_back['Far'], ship_thrust['BackwardStrong'])
        rule23 = ctrl.Rule(asteroid_front['ReallyClose'] | asteroid_back['ReallyFar'], ship_thrust['BackwardStrong'])
        rule24 = ctrl.Rule(asteroid_front['Close'] | asteroid_back['Medium'], ship_thrust['BackwardWeak'])
        rule25 = ctrl.Rule(asteroid_front['Close'] | asteroid_back['Far'], ship_thrust['BackwardStrong'])
        rule26 = ctrl.Rule(asteroid_front['Close'] | asteroid_back['ReallyFar'], ship_thrust['BackwardStrong'])

        rule27 = ctrl.Rule(asteroid_front['Medium'] | asteroid_back['ReallyClose'], ship_thrust['ForwardWeak'])
        rule28 = ctrl.Rule(asteroid_front['Far'] | asteroid_back['ReallyClose'], ship_thrust['ForwardStrong'])
        rule29 = ctrl.Rule(asteroid_front['ReallyFar'] | asteroid_back['ReallyClose'], ship_thrust['ForwardStrong'])
        rule30 = ctrl.Rule(asteroid_front['Medium'] | asteroid_back['Close'], ship_thrust['ForwardWeak'])
        rule31 = ctrl.Rule(asteroid_front['Far'] | asteroid_back['Close'], ship_thrust['ForwardStrong'])
        rule32 = ctrl.Rule(asteroid_front['ReallyFar'] | asteroid_back['Close'], ship_thrust['ForwardStrong'])

        # rule = ctrl.Rule(asteroid_front[''] | asteroid_back[''], ship_thrust[''])

        #DEBUG
        #bullet_time.view()
        #theta_delta.view()
        #ship_turn.view()
        #ship_fire.view()

        # Declare the fuzzy controller, add the rules
        # This is an instance variable, and thus available for other methods in the same object. See notes.
        # self.targeting_control = ctrl.ControlSystem([rule1, rule2, rule3, rule4, rule5, rule6, rule7, rule8, rule9, rule10, rule11, rule12, rule13, rule14, rule15])

        self.targeting_control = ctrl.ControlSystem()
        self.targeting_control.addrule(rule1)
        self.targeting_control.addrule(rule2)
        self.targeting_control.addrule(rule3)
        self.targeting_control.addrule(rule4)
        self.targeting_control.addrule(rule5)
        self.targeting_control.addrule(rule6)
        self.targeting_control.addrule(rule7)
        self.targeting_control.addrule(rule8)
        self.targeting_control.addrule(rule9)
        self.targeting_control.addrule(rule10)
        self.targeting_control.addrule(rule11)
        self.targeting_control.addrule(rule12)
        self.targeting_control.addrule(rule13)
        self.targeting_control.addrule(rule14)
        self.targeting_control.addrule(rule15)
        self.targeting_control.addrule(rule16)
        self.targeting_control.addrule(rule17)
        self.targeting_control.addrule(rule18)
        self.targeting_control.addrule(rule19)
        self.targeting_control.addrule(rule20)
        self.targeting_control.addrule(rule21)
        self.targeting_control.addrule(rule22)
        self.targeting_control.addrule(rule23)
        self.targeting_control.addrule(rule24)
        self.targeting_control.addrule(rule25)
        self.targeting_control.addrule(rule26)
        self.targeting_control.addrule(rule27)
        self.targeting_control.addrule(rule28)
        self.targeting_control.addrule(rule29)
        self.targeting_control.addrule(rule30)
        self.targeting_control.addrule(rule31)
        self.targeting_control.addrule(rule32)

    def find_closest_asteroids(self, ship, asteroids):
        front_closest = None
        back_closest = None

        ship_x, ship_y = ship["position"]
        ship_heading = ship["heading"]

        for asteroid in asteroids:
            asteroid_x, asteroid_y = asteroid["position"]

            # Calculate the angle between the ship's heading and the asteroid
            angle_to_asteroid = math.degrees(math.atan2(asteroid_y - ship_y, asteroid_x - ship_x))

            # Calculate the angle difference between the ship's heading and the angle to the asteroid
            angle_difference = (angle_to_asteroid - ship_heading + 360) % 360

            # Check if the asteroid is in the front 180 degrees or back 180 degrees
            if 0 <= angle_difference <= 180:
                if front_closest is None or (asteroid_x - ship_x)**2 + (asteroid_y - ship_y)**2 < (front_closest["position"][0] - ship_x)**2 + (front_closest["position"][1] - ship_y)**2:
                    front_closest = asteroid
            else:
                if back_closest is None or (asteroid_x - ship_x)**2 + (asteroid_y - ship_y)**2 < (back_closest["position"][0] - ship_x)**2 + (back_closest["position"][1] - ship_y)**2:
                    back_closest = asteroid

        return front_closest, back_closest

    def calculate_distance(self, p1, p2):
        x1, y1 = p1
        x2, y2 = p2
        distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        return distance

    def actions(self, ship_state: Dict, game_state: Dict) -> Tuple[float, float, bool]:
        """
        Method processed each time step by this controller.
        """
        # These were the constant actions in the basic demo, just spinning and shooting.
        #thrust = 0 <- How do the values scale with asteroid velocity vector?
        #turn_rate = 90 <- How do the values scale with asteroid velocity vector?
        
        # Answers: Asteroid position and velocity are split into their x,y components in a 2-element ?array each.
        # So are the ship position and velocity, and bullet position and velocity. 
        # Units appear to be meters relative to origin (where?), m/sec, m/sec^2 for thrust.
        # Everything happens in a time increment: delta_time, which appears to be 1/30 sec; this is hardcoded in many places.
        # So, position is updated by multiplying velocity by delta_time, and adding that to position.
        # Ship velocity is updated by multiplying thrust by delta time.
        # Ship position for this time increment is updated after the the thrust was applied.

        # My demonstration controller does not move the ship, only rotates it to shoot the nearest asteroid.
        # Goal: demonstrate processing of game state, fuzzy controller, intercept computation 
        # Intercept-point calculation derived from the Law of Cosines, see notes for details and citation.

        # Find the closest asteroid (disregards asteroid velocity)
        ship_pos_x = ship_state["position"][0]     # See src/kesslergame/ship.py in the KesslerGame Github
        ship_pos_y = ship_state["position"][1]       
        closest_asteroid = None
        
        for a in game_state["asteroids"]:
            #Loop through all asteroids, find minimum Eudlidean distance
            curr_dist = math.sqrt((ship_pos_x - a["position"][0])**2 + (ship_pos_y - a["position"][1])**2)
            if closest_asteroid is None :
                # Does not yet exist, so initialize first asteroid as the minimum. Ugh, how to do?
                closest_asteroid = dict(aster = a, dist = curr_dist)
                
            else:    
                # closest_asteroid exists, and is thus initialized. 
                if closest_asteroid["dist"] > curr_dist:
                    # New minimum found
                    closest_asteroid["aster"] = a
                    closest_asteroid["dist"] = curr_dist

        # closest_asteroid is now the nearest asteroid object. 
        # Calculate intercept time given ship & asteroid position, asteroid velocity vector, bullet speed (not direction).
        # Based on Law of Cosines calculation, see notes.
        
        # Side D of the triangle is given by closest_asteroid.dist. Need to get the asteroid-ship direction
        #    and the angle of the asteroid's current movement.
        # REMEMBER TRIG FUNCTIONS ARE ALL IN RADAINS!!!
        
        asteroid_ship_x = ship_pos_x - closest_asteroid["aster"]["position"][0]
        asteroid_ship_y = ship_pos_y - closest_asteroid["aster"]["position"][1]
        
        asteroid_ship_theta = math.atan2(asteroid_ship_y,asteroid_ship_x)
        
        asteroid_direction = math.atan2(closest_asteroid["aster"]["velocity"][1], closest_asteroid["aster"]["velocity"][0]) # Velocity is a 2-element array [vx,vy].
        my_theta2 = asteroid_ship_theta - asteroid_direction
        cos_my_theta2 = math.cos(my_theta2)
        # Need the speeds of the asteroid and bullet. speed * time is distance to the intercept point
        asteroid_vel = math.sqrt(closest_asteroid["aster"]["velocity"][0]**2 + closest_asteroid["aster"]["velocity"][1]**2)
        bullet_speed = 800 # Hard-coded bullet speed from bullet.py
        
        # Determinant of the quadratic formula b^2-4ac
        targ_det = (-2 * closest_asteroid["dist"] * asteroid_vel * cos_my_theta2)**2 - (4*(asteroid_vel**2 - bullet_speed**2) * closest_asteroid["dist"])
        
        # Combine the Law of Cosines with the quadratic formula for solve for intercept time. Remember, there are two values produced.
        intrcpt1 = ((2 * closest_asteroid["dist"] * asteroid_vel * cos_my_theta2) + math.sqrt(targ_det)) / (2 * (asteroid_vel**2 -bullet_speed**2))
        intrcpt2 = ((2 * closest_asteroid["dist"] * asteroid_vel * cos_my_theta2) - math.sqrt(targ_det)) / (2 * (asteroid_vel**2-bullet_speed**2))
        
        # Take the smaller intercept time, as long as it is positive; if not, take the larger one.
        if intrcpt1 > intrcpt2:
            if intrcpt2 >= 0:
                bullet_t = intrcpt2
            else:
                bullet_t = intrcpt1
        else:
            if intrcpt1 >= 0:
                bullet_t = intrcpt1
            else:
                bullet_t = intrcpt2
                
        # Calculate the intercept point. The work backwards to find the ship's firing angle my_theta1.
        intrcpt_x = closest_asteroid["aster"]["position"][0] + closest_asteroid["aster"]["velocity"][0] * bullet_t
        intrcpt_y = closest_asteroid["aster"]["position"][1] + closest_asteroid["aster"]["velocity"][1] * bullet_t
        
        my_theta1 = math.atan2((intrcpt_y - ship_pos_y),(intrcpt_x - ship_pos_x))
        
        # Lastly, find the difference betwwen firing angle and the ship's current orientation. BUT THE SHIP HEADING IS IN DEGREES.
        shooting_theta = my_theta1 - ((math.pi/180)*ship_state["heading"])
        
        # Wrap all angles to (-pi, pi)
        shooting_theta = (shooting_theta + math.pi) % (2 * math.pi) - math.pi
        
        # Pass the inputs to the rulebase and fire it
        shooting = ctrl.ControlSystemSimulation(self.targeting_control,flush_after_run=1)
        
        
        asteroid_front, asteroid_back = self.find_closest_asteroids(ship_state, game_state["asteroids"])

        if asteroid_front is None:
            front = (1000,1000)
        else:
            front = asteroid_front["position"]

        if asteroid_back is None:
            back = (1000,1000)
        else:
            back = asteroid_back["position"]

        asteroid_front_dist = self.calculate_distance(ship_state["position"], front)
        asteroid_back_dist = self.calculate_distance(ship_state["position"], back)

        # print("Front: ", asteroid_front_dist, " | Back: ", asteroid_back_dist)

        shooting.input['bullet_time'] = bullet_t
        shooting.input['theta_delta'] = shooting_theta
        shooting.input['asteroid_front'] = asteroid_front_dist
        shooting.input['asteroid_back'] = asteroid_back_dist
        
        shooting.compute()
        
        # Get the defuzzified outputs
        turn_rate = shooting.output['ship_turn']
        thrust = shooting.output['ship_thrust']

        if shooting.output['ship_fire'] >= 0:
            fire = True
        else:
            fire = False
        
        self.eval_frames +=1
        
        #DEBUG
        # print("ship_position: ", ship_state["position"], "  | ship_thrust:", thrust)

        # print(thrust, bullet_t, shooting_theta, turn_rate, fire)
        
        return thrust, turn_rate, fire

    @property
    def name(self) -> str:
        return "ScottDick Controller"

def generateThrustChromosome():
    # Generate a random chromosome value with some values being hard coded.

    sortedArr = np.sort(np.random.randint(-380, 380, 15)).tolist()

    b = 100 # buffer to create intersections

    BackwardStrong = [sortedArr[0]-b, sortedArr[1], sortedArr[2]+b]
    BackwardWeak = [sortedArr[3]-b, sortedArr[4], sortedArr[5]+b]
    Neutral = [sortedArr[6]-b, sortedArr[7], sortedArr[8]+b]
    ForwardWeak = [sortedArr[9]-b, sortedArr[10], sortedArr[11]+b]
    ForwardStrong = [sortedArr[12]-b, sortedArr[13], sortedArr[14]+b]

    chromosome = BackwardStrong + BackwardWeak + Neutral + ForwardWeak + ForwardStrong
    return chromosome

def fitness(chromosome):
    try:
        my_test_scenario = Scenario(name='Test Scenario',
                                    num_asteroids=5,
                                    ship_states=[
                                        {'position': (400, 400), 'angle': 90, 'lives': 3, 'team': 1},
                                        # {'position': (500, 400), 'angle': 90, 'lives': 3, 'team': 2},
                                    ],
                                    map_size=(1000, 800),
                                    time_limit=60,
                                    ammo_limit_multiplier=0,
                                    stop_if_no_ammo=False)

        game_settings = {'perf_tracker': True,
                        'graphics_type': GraphicsType.Tkinter,
                        'realtime_multiplier': 1,
                        'graphics_obj': None}
        # game = KesslerGame(settings=game_settings) # Use this to visualize the game scenario GRAPHICS
        game = TrainerEnvironment(settings=game_settings) # Use this for max-speed, no-graphics simulation WITHOUT GRAPHICS
        pre = time.perf_counter()
        score, perf_data = game.run(scenario=my_test_scenario, controllers = [GroupControllerGA(chromosome.gene_value_list[0])])
        # print('Scenario eval time: '+str(time.perf_counter()-pre))
        print(score.stop_reason)
        
        total_asteroids_hit = [team.asteroids_hit for team in score.teams]
        print(total_asteroids_hit)

        # print('Deaths: ' + str([team.deaths for team in score.teams]))
        # print('Accuracy: ' + str([team.accuracy for team in score.teams]))
        # print('Mean eval time: ' + str([team.mean_eval_time for team in score.teams]))
        # print('Evaluated frames: ' + str([controller.eval_frames for controller in score.final_controllers]))
        
        return total_asteroids_hit[0]
    
    except Exception as e:
        print(f"Exception in the fitness function: {e}")

def findBestChromosome():
    ga = EasyGA.GA()
    ga.gene_impl = lambda: generateThrustChromosome()
    ga.chromosome_length = 1
    ga.population_size = 10
    ga.target_fitness_type = 'max'
    ga.generation_goal = 2
    ga.fitness_function_impl = fitness
    ga.evolve()

    # print(ga.population[0])
    return ga.population[0]


bestChromosome = findBestChromosome()
print("Best Chromosome: ", bestChromosome)
