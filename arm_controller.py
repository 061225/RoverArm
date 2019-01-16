

from UDPComms import Subscriber, timeout
from roboclaw_interface import RoboClaw
import math
import time


FIRST_LINK = 1000
SECOND_LINK = 1000

# native angles = 0 at extension

def find_serial_port():
    return '/dev/ttyUSB0'
    return '/dev/ttyACM0'
    return '/dev/tty.usbmodem1141'

class Vector(list):

    def __add__(self,other):
        assert len(self) == len(other)
        return Vector( a+b for a,b in zip(self,other) )

    def __sub__(self,other):
        assert len(self) == len(other)
        return Vector( a-b for a,b in zip(self,other) )

    def __mul__(self,other):
        return Vector( other * a for a in self )

    def __rmul__(self,other):
        return Vector.__mul__(self,other)  

    def norm(self):
        return math.sqrt(sum(a**2 for a in self))

    def __repr__(self):
        return "Vector(" + super().__repr__() + ")"

class Arm:
    def __init__(self):
        self.target_vel = Subscriber(8410)

        self.xyz_names = ["x", "y"]

        self.motor_names = ["shoulder",
                            "elbow"]

        self.native_positions = { motor:0 for motor in self.motor_names}
        self.CPR = { motor:100 for motor in self.motor_names}

        self.rc = RoboClaw(find_serial_port(), names = self.motor_names, addresses = [128] ) # addresses = [128, 129, 130])

        while 1:
            self.update()
            time.sleep(100)

    def send_speeds(self, speeds):
        for motor in self.motor_names:
            self.rc.drive_speed(motor, speeds[motor])

    def get_location(self):
        for motor in self.motor_names:
            self.native_positions[motor] = 2 * math.pi * self.rc.get_encoder(motor)/self.CPR[motor]

        self.xyz_positions = self.native_to_xyz(self.native_positions)

    def xyz_to_native(self, xyz):
        native = {}

        distance = math.sqrt(xyz['x']**2 + xyz['y']**2)
        angle = math.atan2(xyz['x'], xyz['y'])

        offset = math.acos( ( FIRST_LINK**2 + distance**2 - SECOND_LINK**2  ) / (2*distance * FIRST_LINK) )
        inside = math.acos( ( FIRST_LINK**2 + SECOND_LINK**2 - distance**2  ) / (2*SECOND_LINK * FIRST_LINK) )

        native['shoulder'] = angle + offset
        native['elbow'] = - (math.pi - inside) 

        return native

    def native_to_xyz(self, native):
        xyz = {}
        xyz['x'] = FIRST_LINK * math.sin(native['shoulder']) + SECOND_LINK * math.sin(native['shoulder'] + native['elbow'])
        xyz['y'] = FIRST_LINK * math.cos(native['shoulder']) + SECOND_LINK * math.cos(native['shoulder'] + native['elbow'])
        return xyz

    def dnative(self, dxyz):
        x = self.xyz_positions['x']
        y = self.xyz_positions['y']

        shoulder_diff_x = y/(x**2 + y**2) - (x/(FIRST_LINK*math.sqrt(x**2 + y**2)) - x*(FIRST_LINK**2 - SECOND_LINK**2 + x**2 + y**2)/(2*FIRST_LINK*(x**2 + y**2)**(3/2)))/math.sqrt(1 - (FIRST_LINK**2 - SECOND_LINK**2 + x**2 + y**2)**2/(4*FIRST_LINK**2*(x**2 + y**2)))

        shoulder_diff_y = -x/(x**2 + y**2) - (y/(FIRST_LINK*math.sqrt(x**2 + y**2)) - y*(FIRST_LINK**2 - SECOND_LINK**2 + x**2 + y**2)/(2*FIRST_LINK*(x**2 + y**2)**(3/2)))/math.sqrt(1 - (FIRST_LINK**2 - SECOND_LINK**2 + x**2 + y**2)**2/(4*FIRST_LINK**2*(x**2 + y**2)))

        elbow_diff_x = -x/(FIRST_LINK*SECOND_LINK*math.sqrt(1 - (FIRST_LINK**2 + SECOND_LINK**2 - x**2 - y**2)**2/(4*FIRST_LINK**2*SECOND_LINK**2)))

        elbow_diff_y = -y/(FIRST_LINK*SECOND_LINK*math.sqrt(1 - (FIRST_LINK**2 + SECOND_LINK**2 - x**2 - y**2)**2/(4*FIRST_LINK**2*SECOND_LINK**2)))

        dnative = {}
        dnative['shoulder'] = shoulder_diff_x * x + shoulder_diff_y * y 
        dnative['elbow']    = elbow_diff_x * x    + elbow_diff_y * y 
        return dnative


    def update(self):
        self.get_location()

        try:
            speeds = self.dnative_dxyz(self.target_vel.get())
        except timeout:
            speed = {motor: 0 for motor in self.motor_names}
        except:
            speed = {motor: 0 for motor in self.motor_names}
            raise
        finally:
            self.send_speeds(speeds)





