import struct
import socket

'''

Remote is whatever is running the python program
PTR is the gimbal

'''
# controll characters
STX = 0x02  # Start of text sent by remote
ETX = 0x03  # end of text sent by remote/PTR
ACK = 0x06  # Acknowledge sent by PTR
NAK = 0x15  # Not Acknowledge sent by PTR
ESC = 0x1B  # escape characters


class GimbalController:

    def __init__(self, sock=None):
        '''
        Function to initilize the socket
        can change socket if it is not tcp which is what the below code is
        '''
        if sock is None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        else:
            self.sock = sock

    def connect(self, host, port):
        '''
        connect to host with given port
        need this method to controll multiple gimbals
        '''
        self.sock.connect((host, port))

    # stubbed out method
    def send(self, packetArray):
        '''
        after just a quick thought about this we would have to make the packet array a 
        string to send over socket
        '''
        print(bytearray(packetArray))
        self.sock.send(bytearray(packetArray))

    # stubbed out method
    def received(self):
        '''
        we might have to do the same thing with the method above
        '''
        return self.sock.recv(1024)

    def closeSocket(self):
        '''
        Close the socket to be able to connect to more
        should not need to call __init__ again
        '''
        self.sock.close()

        

    # CommandNumberAndData should be a list of bytes
    def calculateLRC(self, CommandNumberAndData):
        '''
        Calculates lrc by xoring all bits together
        returns lrc or none if CommandNumberAndData is none
        '''
        lrc = 0
        if CommandNumberAndData is not None:
            for byte in CommandNumberAndData:
                if isinstance(byte, int):
                    lrc ^= byte
                else:
                    lrc ^= int.from_bytes(byte, byteorder='little', signed=True)
            return lrc
        else:
            return None

    def convertIntegerToShort(self, integer):
        '''
        This replaces the setvalue24 https://github.com/ahearnkyle/GimbalProject/wiki/gimbal-connection
        
        returns the short value or none if index out of bounds

        This method will take an integer between 32768 and -32768 and will convert that
        integer into a short int and return that as a byte string so 
        32768 now equals b'\xff\x7f' with the \ signifying the different bits

        This satisfies the following section of the protocol manual
        
        Passing Integer Values:
        As noted in the protocol command descriptions, some values sent between the remote and PTR units are integer
        values.  These integer values should be passed and received as 16-bit signed two's-complement little endian
        integers simply split between two bytes.  The first byte should represent the LSB of the integer with the second byte
        containing the MSB of the integer.  Negative values are represented as the two's-complement of the positive value 
        '''
        if integer > 32767 or integer < -32768:
            return None
        else:
            # < stands for little endian and h is for short
            return struct.pack("<h", integer)

    def getStatusJog(self, pan, tilt, speed, osl, stop, reset):
        packetArray = []
        command = 0x31
        bitsetCommand = (0 | 0 | 0 | 0 | 0 | osl | stop | reset)
        packetArray.append(STX)
        packetArray.append(0x00)
        packetArray.append(command)
        packetArray.append(bitsetCommand)
        if speed is 0:
            '''
            Keep gimbel still
            '''
            packetArray.append(0x00)
            packetArray.append(0x00)
        else:
            pass
        '''
        Auxiliary byte or bitset

        From the controller protocol 
        
        The two auxiliary commands are currently not implemented in hardware but have the potential to provide focus and
        zoom control, camera switching, time stamping commands, etc. They should be written as 0.
        '''
        packetArray.append(0x00)
        packetArray.append(0x00)
        packetArray.append(self.calculateLRC(packetArray[2:7]))
        packetArray.append(ETX)

        self.connect('192.168.0.36', 10001)
        print("connected")
        self.send(packetArray)
        print("sent packet")

        # get return packet
        packet = self.received()

        print(packet)

    def moveToHome(self):
        '''
        This moves to preset position number 31
        '''
        packetArray = []
        command = 0x36
        packetArray.append(STX)
        packetArray.append(0x00)
        packetArray.append(command)
        packetArray.append(self.calculateLRC(packetArray[2:3]))
        '''
        gets the second item in list. Must use a slice so that it returns a list itself since 
        calculateLRC expexts a list
        '''
        packetArray.append(ETX)

        # send packet
        self.connect('192.168.0.36', 10001)
        print("connected")
        self.send(packetArray)
        print("sent packet")

        # get return packet
        packet = self.received()

        print(packet)

    def moveToEnteredCoordinate(self, panCoord, tiltCoord):
        '''
        The Coordinate must be the desired position to the 1/10th degree multiplied by 10
        so 90.0 degrees is 900 and 45.9 is 459

        If you only want to pan then send 9999 (999.9 degress) as tilt coordinate and vise versa

        The PTR will also account for angle offset to make sure commands are not out of bounds
        '''
        packetArray = []
        command = 0x33
        packetArray.append(STX)
        packetArray.append(command)
        packetArray.append(self.convertIntegerToShort(panCoord))
        packetArray.append(self.convertIntegerToShort(tiltCoord))
        packetArray.append(self.calculateLRC(packetArray[1:4]))
        packetArray.append(ETX)     

        # send packet
        self.send(packetArray)

        # get return packet
        self.received()  

    def moveToAbsoluteZero(self):
        '''
        This command will return the PTR to the stored center 
        '''
        packetArray = []
        command = 0x35
        packetArray.append(STX)
        packetArray.append(command)
        packetArray.append(self.calculateLRC(packetArray[1:2])) 
        packetArray.append(ETX)

        # send packet
        self.send(packetArray)

        # get return packet
        self.received()

    def retrievePresetTableEntry(self, preset):
        '''
        Takes the preset, which must be in hex (0x00-0x1F). Returns the stored coordinate position
        '''
        packetArray = []
        command = 0x40
        packetArray.append(STX)
        packetArray.append(0x00)
        packetArray.append(command)
        packetArray.append(preset)
        packetArray.append(self.calculateLRC(packetArray[2:4])) 
        packetArray.append(ETX)

        # send packet
        self.connect('192.168.0.36', 10001)
        print("connected")
        self.send(packetArray)
        print("sent packet")

        # get return packet
        packet = self.received()

        print(packet)

    def saveCurrentPositionAsPreset(self, preset):
        '''
        Takes the preset, which must be in hex (0x00-0x1F) and sets the current position to that preset
        '''
        packetArray = []
        command = 0x42
        packetArray.append(STX)
        packetArray.append(command)
        packetArray.append(preset)
        packetArray.append(self.calculateLRC(packetArray[1:3])) 
        packetArray.append(ETX)

        # send packet
        self.send(packetArray)

        # get return packet
        self.received()

def main():
    #print(convertIntegerToShort(-2))
    controller = GimbalController()
    controller.getStatusJog(1,1,0,4,0,0)
    #controller.moveToHome()
    #controller.retrievePresetTableEntry(0x00)
    #controller.moveToEnteredCoordinate(200, 123)


if __name__ == '__main__':
    main()
