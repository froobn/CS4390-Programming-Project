import sys
import time
import os
import heapq

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
        the main life loop of the node, responsible for receiving, sending, and outputing all that was received, then the nodes life ends
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
        assert(5 <= duration <= 180)
        assert(0 <= dest_id <=9)
        assert(all(31 < ord(char) < 127 for char in message))
        assert(0 <= starting_time <= duration or (starting_time == -1 and message == ""))
        assert(message != "" or (starting_time == -1 and message == ""))
        for neighbor in neighbors:
            assert(0 <= neighbor <=9)
            assert(neighbor != id)

        # SET VARIABLES
        self.id = id
        self.duration = duration
        self.dest_id = dest_id
        self.message = message # END OF MESSAGE DELIMITER
        self.starting_time = starting_time
        self.neighbors = neighbors
        self.neighbor_pulses = {neighbor: 20 for neighbor in neighbors}

        # LAYERS
        self.Transport = Transport_Layer(self)
        self.Network = Network_Layer(self)
        self.Datalink = Datalink_Layer(self)
        

        # MAIN NODE LIFECYCLE
        self.live()

    def live(self):
        print("OPENING NODE ", self.id)
        for sec in range(self.duration):
            # EVERY 10 SECONDS
            if sec % 10 == 0:
                self.Network.send_lsp()

            # DATA LINK RECIEVE FROM CHANNEL
            self.Datalink.receive_from_channel()

            # NACK TIMER
            for source, timer in self.Transport.timeout.items():
                if timer > 0:
                    self.Transport.timeout[source] -= 1
                if timer == 0:
                    self.Transport.do_timeout(source)
                    self.Transport.timeout[source] = -1

            if self.Transport.nack_timer >= 0:
                self.Transport.nack_timer -= 1
            if self.Transport.nack_timer == 0 and len(self.Transport.ack_buffer) > 0:
                self.Transport.retransmit_ack_buffer()


            # TRANSPORT SEND
            if sec == self.starting_time:
                self.Transport.send()

            # PRUNE ANY DEAD NEIGHBORS
            dead_neighbors = []
            for neighbor in self.neighbor_pulses:
                self.neighbor_pulses[neighbor] -= 1
                if self.neighbor_pulses[neighbor] <= 0:
                    dead_neighbors.append(neighbor)
            
            for dn in dead_neighbors:
                self.neighbor_pulses.pop(dn)
                self.neighbors.remove(dn)



            # SLEEP 1 SECOND
            time.sleep(1)
        
        # TRANSPORT OUTPUT ALL RECIEVED
        self.Transport.output_all()
        print("CLOSING: ", self.id)
        return


# ----------------------- LAYERS -----------------------
#############################################################
class Transport_Layer:
    '''
    Responsible for sending the message to its destination by breaking up the message into frames and giving it to the network layer.
    Responsible for receiving messages from the network layer that are addressed to this node.
    Responsible for outputting the file called "nodeXreceived" where X is the id of the source node and contains all the strings that have been receieved with the following format ----> "From X receieved: this is a message from X" 
    '''
    # Message format ---> DidDESTseqnumFRAME
    # id ---> single digit source id
    # DEST ---> single digit destination id
    # seqnum ---> double digit (or padded with zeros) sequence number for message
    # FRAME ---> the split frame, only 5 bytes long per frame
    def __init__(self, parent_node: Node) -> None:
        self.parent_node = parent_node
        self.sequence_number = 0

        # BUFFER FOR INCOMING MESSAGES AND FOR RESENDING MESSAGES
        self.buffer = []
        self.ack_buffer = []
        
        # NACK SENDING
        self.nackable = {}
        self.timeout = {}
        self.nack_timer = -1

    def send(self):
        if(self.parent_node.message == ""): # NON MESSAGING NODE
            return
        
        # ELSE: SEND NODE MESSAGE TO DESTINATION
        frames = [self.parent_node.message[i:i+5] for i in range(0, len(self.parent_node.message), 5)]
        for frame in frames:

            # Format the data message
            data_message = 'D{}{}{:02d}{}'.format(self.parent_node.id, self.parent_node.dest_id, self.sequence_number, frame)
            
            # Send the data message to the network layer
            self.parent_node.Network.receive_from_transport(data_message, self.parent_node.dest_id)
            self.ack_buffer.append((self.sequence_number, data_message))
            # Update sequence number
            self.sequence_number = (self.sequence_number + 1) % 100
            self.nack_timer = 20

    def nack(self, dest, seq_num):

        nack_message = "N{}{}{:02d}".format(self.parent_node.id, dest, seq_num)
        self.parent_node.Network.receive_from_transport(nack_message, int(dest))

    def do_timeout(self, source: int):
        final_nack = True
        for i in range(self.sequence_number):
            to_nack = i    
            for msg in self.buffer:
                if int(msg.seq_num) == i and int(msg.source) == int(source):
                    to_nack = -1
            if to_nack >= 0:
                self.nack(int(source), i)
                final_nack = False
        if final_nack:
            self.nack(source, self.sequence_number+1)
            
    def retransmit_ack_buffer(self):
        for msg in self.ack_buffer:
            self.parent_node.Network.receive_from_transport(msg[1], self.parent_node.dest_id)

    def receieve_from_network(self, message: str):
        msg_type = message[0]

        if msg_type == "D": # DATA MESSAGE
            source = message[1]
            seq_num = message[3:5]
            data = message[5:]
            if int(seq_num) >= self.sequence_number:
                self.sequence_number = int(seq_num) + 1
            self.buffer.append(Packet(seq_num=seq_num, message=data, source=source,msg_type=msg_type))
            self.timeout[source] = 5

        elif msg_type == "N":   #NACK'D!
            seq_num = int(message[3:5])
            print("NACK RECIEVED: ", seq_num)
            if seq_num > self.sequence_number:
                self.ack_buffer = []
            for msg in self.ack_buffer:
                if msg[0] < seq_num:
                    self.ack_buffer.remove(msg)
                elif msg[0] == seq_num:
                    self.parent_node.Network.receive_from_transport(msg[1], self.parent_node.dest_id)

    def output_all(self):
        reassembled = ""
        # FIX POTENTIAL REORDERING
        sorted_buffer = sorted(self.buffer, key=lambda p: (p.source,p.seq_num))
        if len(sorted_buffer) == 0:
            return
        curr_source = sorted_buffer[0].source
        for message in sorted_buffer:
            if(message.source != curr_source):
                with open("output/thenode{}recieved.txt".format(self.parent_node.id), "a") as output:
                    output.write("from {} receieved: {}\n".format(curr_source, reassembled))
                reassembled = ""
            curr_source = message.source
            reassembled += message.message
        with open("output/thenode{}recieved.txt".format(self.parent_node.id), "a") as output:
            output.write("from {} receieved: {}\n".format(curr_source, reassembled))

#############################################################
class Network_Layer:
    '''
    Responsible for routing and determining if the parent_node is the messages destination to then send to the transport layer
    '''
    # Message format ---> "DdestLENmessage"
    # dest ---> one digit id
    # LEN ---> two digit length (padding 0s if needed)
    # message ---> message data
    def __init__(self, parent_node: Node) -> None:
        self.parent_node = parent_node
        self.routing_table = {}

        self.lsp_seq_num = 0
        self.lsp_data = {}
        self.lsp_seq_num_table = {}
        

    def receive_from_transport(self, message: str, dest: int):
        if dest not in self.routing_table.keys():
            print("NO ROUTE",self.parent_node.id, "-->",dest)
            print(self.routing_table, self.lsp_data)
            return
        
        data_message = 'D{}{:02d}{}'.format(dest,len(message), message)
        if len(data_message) < 15:
            data_message = data_message.ljust(15, ' ')
        self.parent_node.Datalink.receive_from_network(data_message, self.routing_table[dest])

    def receive_from_datalink(self, message: str, neighbor_id: int):
    
        # GENERAL DATA MESSAGES
        if message[0] == "D":
            dest = int(message[1])
            length = int(message[2:4])
            data_message = message[4:4+length]
            if(dest == self.parent_node.id):
                self.parent_node.Transport.receieve_from_network(data_message)
            else: # ROUTE
                if dest in self.routing_table.keys():
                    self.parent_node.Datalink.receive_from_network(message,self.routing_table[dest])
                else:
                    print("NO ROUTE",self.parent_node.id, "-->",dest)
                    print(type(self.parent_node.id), type(dest), self.routing_table)

        # LSP MESSAGES
        elif message[0] == "L":
            # PARSE DATA
            source = int(message[1])
            seq_num = int(message[2:4])
            source_neighbors = message[4:].strip()


            for neighbor in source_neighbors:
                if int(neighbor) == self.parent_node.id:
                    self.parent_node.neighbor_pulses[source] = 20
                    if source not in self.parent_node.neighbors:
                        self.parent_node.neighbors.append(source)


            if not source in self.lsp_seq_num_table.keys():
                self.lsp_seq_num_table[source] = seq_num
            elif seq_num > self.lsp_seq_num_table[source]:
                self.lsp_seq_num_table[source] = seq_num
            else:
                return
            
            if source not in self.lsp_data or seq_num > self.lsp_data.get(source).seq_num:
                self.lsp_data[source] = LSP(seq_num, message, source, source_neighbors)

            for neighbor in self.parent_node.neighbors:
                if neighbor != source and str(neighbor) not in source_neighbors:
                    self.parent_node.Datalink.receive_from_network(message,neighbor)
            self.network_route()
    
    def send_lsp(self):
        neighbors = ""
        for neighbor in self.parent_node.neighbors:
            neighbors+=str(neighbor)
        packet = "L{}{:02d}{}".format(self.parent_node.id,self.lsp_seq_num, neighbors)
        if len(packet) < 15:
            packet = packet.ljust(15, ' ')
        self.lsp_seq_num = (self.lsp_seq_num + 1) % 100
        for neighbor in self.parent_node.neighbors:
            self.parent_node.Datalink.receive_from_network(packet,neighbor)
        
    def network_route(self):
        # self.routing_table = {}
        # self.lsp_seq_num_table = {}
        distances = {}
        self.routing_table[self.parent_node.id] = self.parent_node.id
        for neighbor in self.parent_node.neighbors:
            distances[neighbor] = 1
            self.routing_table[neighbor] = neighbor
        for source, lsp in self.lsp_data.items():
            distances[int(source)] = sys.maxsize
            for neighbor in lsp.neighbors:
                distances[int(neighbor)] = sys.maxsize
        distances[self.parent_node.id] = 0


        queue = [(0, self.parent_node.id)]

        while len(queue) > 0:
            current_distance, current_node = heapq.heappop(queue)

            if current_distance > distances[current_node]:
                continue

            if current_node == self.parent_node.id:
                for neighbor in self.parent_node.neighbors:
                    distance = current_distance + 1

                    if distance < distances[neighbor]:
                        distances[neighbor] = distance
                        heapq.heappush(queue, (distance, neighbor))
            elif self.lsp_data.get(current_node):
                for neighbor in self.lsp_data[current_node].neighbors:
                    distance = current_distance + 1

                    if distance < distances[int(neighbor)]:
                        distances[int(neighbor)] = distance
                        self.routing_table[int(neighbor)] = current_node
                        heapq.heappush(queue, (distance, int(neighbor)))


        for node in self.routing_table:
            if self.routing_table[node] == node:
                continue
            next_hop = self.routing_table[node]
            while next_hop != node and next_hop != self.parent_node.id and next_hop not in self.parent_node.neighbors:
                next_hop = self.routing_table[next_hop]
            self.routing_table[node] = next_hop

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
        gives network layer message to this (datalink) layer
        outputs to the output channel file the message given by the network layer
        '''
        assert(len(message) == 15)

        assert(next_hop in self.parent_node.neighbors)

        # GET CHECKSUM
        message_ascii = message.encode('ascii')
        checksum = sum(message_ascii) % 100
        
        # FORMAT MESSAGE
        formatted_message = 'XX{:15}{}'.format(message_ascii.decode('ascii'), str(checksum).zfill(2))
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
            with open('channels/'+channel, 'r') as f:
                f.read(self.bookmarks[channel])
                message = ""
                while True:
                    byte = f.read(1)
                    if not byte:
                        break
                    message += byte
                    self.bookmarks[channel] += 1
                    if len(message) >= 19: # END OF FRAME
                        # CHECK THE FORMATTING
                        message_ascii = message[2:17].encode('ascii')
                        checksum = sum(message_ascii) % 100
                        if(message[:2] != "XX" or checksum != int(message[17:])):
                            # throw out this packet and nack
                            print("CORRUPTION: ", message)
                            dl_decode = message[2:17]
                            n_decode = dl_decode[4:]
                            seq_num = int(n_decode[3:5])
                            source = int(n_decode[1])
                            self.parent_node.Transport.nack(source, seq_num)
                            while(message != "X"):
                                message = ""
                                recovering_byte = f.read(1)
                                if not byte:
                                    break
                                message += recovering_byte
                            continue
                            
                        
                        # MESSAGE LOOKS GOOD :)
                        self.parent_node.Network.receive_from_datalink(message[2:17], get_channel_io(channel)[0])
                        message=""
                        # PROCESS FRAME
                        


    def set_input_channels(self):
        for filename in os.listdir('channels'):
            if filename in self.input_channels:
                continue
            f = os.path.join('channels', filename)
            if os.path.isfile(f) and get_channel_io(filename)[1] == self.parent_node.id:
                self.input_channels.append(filename)
                self.bookmarks[filename] = 0
#############################################################


def parse_neighbors(input):
    output = []
    for i in range(len(input)):
        output.append(int(input[i]))
    return output
  
def get_channel_io(filename:str):
    digits = [int(s) for s in filename if s.isdigit()]
    X, Y = digits[:1], digits[1:]
    return [X[0], Y[0]]

class Packet:
    def __init__(self, seq_num, message,source,msg_type="D"):
        self.seq_num = seq_num
        self.message = message
        self.source = source
        self.msg_type = msg_type
        self.history = ""

class LSP(Packet):
    def __init__(self, seq_num, message, source, neighbors):
        super().__init__(seq_num, message, source, "L")
        self.neighbors = neighbors

    def __repr__(self) -> str:
        return self.neighbors
    


# ARGUMENT PROCESSING
args = sys.argv

if len(args) > 6 and not args[4].isdigit(): # SOURCE NODES
    node = Node(id=int(args[1]), duration=int(args[2]), dest_id=int(args[3]),message=args[4],starting_time=int(args[5]),neighbors=parse_neighbors(args[6:]))

else: # NON-SOURCE NODES
    try:
        node = Node(id=int(args[1]), duration=int(args[2]), dest_id = int(args[3]), neighbors=parse_neighbors(args[4:]))
    except:
        print('INVALID ARGUMENTS')