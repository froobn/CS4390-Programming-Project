import sys
import time
import os

class Node:
    '''
    A node corresponds to a process in a simulated network, using files to correspond to channels in the network
    ...

    Attributes
    ----------
    id : int
        id of this node (i.e., a number from 0 to 9)
    duration: int
        the duration, in seconds, that the node hsould run before it terminates
    dest_id: int
        the destination id of a process to which the transport protocol should send data
    message: str
        string of arbitrary text which the transport layer will send to the destination
    starting_time: int
        the starting time for the transport layer
    neighbors: list<int>
        list of id's of nighbors of the process 
    Transport: Transport_Layer
        
    Network: Network_Layer
        
    Datalink: Datalink_Layer
        

    Methods
    -------
    live()
        the main life loop of the node, responsible for receiving, sending, and outputing all that was received
    die()
        closes Node
    ''' 
    def __init__(self, id: int, duration: int, neighbors: list, dest_id: int, message: str = "", starting_time: int = -1) -> None:
        '''
            id: id of this node (i.e., a number from 0 to 9)
            duration: the duration, in seconds, that the node hsould run before it terminates
            dest_id: the destination id of a process to which the transport protocol should send data
            message: string of arbitrary text which the transport layer will send to the destination
            starting_time: the starting time for the transport layer
            neighbors: list of id's of nighbors of the process 
        '''
        # ASSERTIONS
        assert(0 <= id <=9)
        assert(30 <= duration <= 120)
        assert(0 <= dest_id <=9)
        assert(all(31 < ord(char) < 127 for char in message))
        assert(0 <= starting_time or (starting_time == -1 and message == ""))  # TODO UPPER LIMIT??
        assert(message != "" or (starting_time == -1 and message == ""))
        for neighbor in neighbors:
            assert(0 <= neighbor <=9)
            assert(neighbor != id)

        # SET VARIABLES
        self.id = id
        self.duration = duration
        self.dest_id = dest_id
        self.message = message
        self.starting_time = starting_time
        self.neighbors = neighbors

        # LAYERS
        self.Transport = Transport_Layer(self)
        self.Network = Network_Layer(self)
        self.Datalink = Datalink_Layer(self)
        

        # MAIN NODE LIFECYCLE
        self.live()
        self.die()

    def live(self):
        print("OPENING NODE ", self.id)
        for sec in range(self.duration):
            # DATA LINK RECIEVE FROM CHANNEL
            self.Datalink.receive_from_channel()

            # TRANSPORT SEND
            self.Transport.send()

            # SLEEP 1 SECOND
            time.sleep(1)
            return # TODO DELETE THIS
        
        # TRANSPORT OUTPUT ALL RECIEVED
        self.Transport.output_all()

    def die(self):
        print("CLOSING NODE ", self.id)
        pass

    def clean_channels(self):
        pass

# ----------------------- LAYERS -----------------------
#############################################################
class Transport_Layer:
    '''
    Responsible for sending the message to its destination by breaking up the message into frames and giving it to the network layer.
    Responsible for receiving messages from the network layer that are addressed to this node.
    Responsible for outputting the file called "nodeXreceived" where X is the id of the source node and contains all the strings that have been receieved with the following format ----> "From X receieved: this is a message from X" 
    '''
    def __init__(self, parent_node: Node) -> None:
        self.parent_node = parent_node
        self.sequence_number = 0

    def send(self, nack_message=""):
        if nack_message:
            self.parent_node.Network.receive_from_transport(nack_message, self.parent_node.dest_id)
            return
        
        # else
        frames = [self.parent_node.message[i:i+5] for i in range(0, len(self.parent_node.message), 5)]
        for frame in frames:

            # Format the data message
            data_message = 'D{}{}{:02d}{}'.format(self.parent_node.id, self.parent_node.dest_id, self.sequence_number, frame)
            
            # Send the data message to the network layer
            self.parent_node.Network.receive_from_transport(data_message, self.parent_node.dest_id)

            # while nack_received is not None:
            #     nack_sn = int(nack_message[3:5])
            #     if nack_sn > self.sequence_number:
            #         break
            #     # Resend
            #     nack_received = self.parent_node.Network.receive_from_transport(data_message, self.parent_node.dest_id)

            self.sequence_number = (self.sequence_number + 1) % 100

    def receieve_from_network(self, message: str, length: int, source: int):
        nack_message = 'N{}{}{:02d}'.format(self.parent_node.id, self.parent_node.dest_id, self.sequence_number)
        self.parent_node.Network.receive_from_transport(nack_message, self.parent_node.dest_id)
        #NACK OR RESEND
        pass

    def output_all(self):
        pass

#############################################################
class Network_Layer:
    '''
    Responsible for routing and determining if the parent_node is the messages destination to then send to the transport layer
    '''
    def __init__(self, parent_node: Node) -> None:
        self.parent_node = parent_node

    def receive_from_transport(self, message: str, dest: int):
        data_message = 'D{}{:02d}{}'.format(dest,len(message), message)
        if len(data_message) < 15:
                data_message = data_message.ljust(15, ' ')
        self.parent_node.Datalink.receive_from_network(data_message, dest)

    def receive_from_datalink(self, message: str, neighbor_id: int):
        pass

    def network_route(self):
        pass

#############################################################
class Datalink_Layer:
    '''
    Responsible for reading bytes of data from the file channel and forming the frames into a complete message, which will then be sent to the network layer.
    Responsible for receiving message from the network layer to then encapsulate them into data link layer messages to append to the file channel.
    '''
    # Message format ---> "XXmessageCS" 
    # CS ---> 2 byte Checksum integer
    # Message ----> 15 bytes
    def __init__(self, parent_node: Node) -> None:
        self.parent_node = parent_node
        self.input_channels = []
        self.bookmarks = {}
    def receive_from_network(self, message: str, next_hop: int):
        '''
        CALLED BY NETWORK LAYER
        gives network layer message to this (datalink) layer
        outputs to the output channel file the message given by the network layer
        '''
        assert(len(message) == 15)

        # GET CHECKSUM
        message_ascii = message.encode('ascii')
        checksum = sum(message_ascii) % 100
        
        # FORMAT MESSAGE
        formatted_message = 'XX{:15}{}\n'.format(message_ascii.decode('ascii'), str(checksum).zfill(2))
        # WRITE TO CHANNEL
        with open("channels/from{}to{}.txt".format(self.parent_node.id, next_hop), "a") as channel:
            channel.write(formatted_message)


    def receive_from_channel(self):
        '''
        reads from each of the input files (channels from each neighbor) 
        MUST READ UNTIL AN EOF HAS ARRIVED FOR ALL INPUT CHANNELS SINCE BYTES MIGHT NOT HAVE ARRIVED YET!
        '''

        # GET CURRENT INPUT CHANNELS
        self.set_input_channels()

        # READ EACH CHANNEL UNTIL EOF FOR EACH CHANNEL
        for channel in self.input_channels:
            print("READING: ", channel)
            with open('channels/'+channel, 'r') as f:
                while True:
                    byte = f.read(1)
                    print(byte)
                    if not byte:
                        break
                # message = ""
                # for idx, line in enumerate(iter(f.readline, '')):
                #     # SKIP ALREADY RECIEVED MESSAGES
                #     if(idx < self.bookmarks[channel]):
                #         continue

                #     # GRAB LINE, MOVE BOOKMARK
                #     message += line
                #     self.bookmarks[channel] += 1
                    

                #     # CHECK FOR MESSAGE COMPLETION
                #     # TODO FIND A WAY TO CHECK FOR END OF MESSAGE
                # # PASS TO NETWORK LAYER
                # if message != "":
                #     self.parent_node.Network.receive_from_datalink(message, get_channel_io(channel)[0])

    def set_input_channels(self):
        for filename in os.listdir('channels'):
            if filename in self.input_channels:
                continue
            f = os.path.join('channels', filename)
            if os.path.isfile(f) and get_channel_io(filename)[1] == self.parent_node.id:
                print("appending: ", filename)
                self.input_channels.append(filename)
                self.bookmarks[filename] = 0
#############################################################


def parse_neighbors(input):
    n = len(input)
    a = input[1:n-1]
    a = a.split(',')
    for idx, val in enumerate(a):
        a[idx] = int(val)
    return a
  
def get_channel_io(filename:str):
    digits = [int(s) for s in filename if s.isdigit()]
    X, Y = digits[:1], digits[1:]
    return [X[0], Y[0]]


# ARGUMENT PROCESSING
args = sys.argv

if len(args) > 6: # SOURCE NODES
    node = Node(id=int(args[1]), duration=int(args[2]), dest_id=int(args[3]),message=args[4],starting_time=int(args[5]),neighbors=parse_neighbors(args[6]))

elif len(args) > 4: # NON-SOURCE NODES
    node = Node(id=int(args[1]), duration=int(args[2]), dest_id = int(args[3]), neighbors=parse_neighbors(args[4]))

else: #INVALID ARGUMENTS
    print('INVALID ARGUMENTS') #TODO write help message

