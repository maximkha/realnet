from os import read
from parse import parse
from math import fabs, floor
import numpy as np

def add(pos1:tuple, pos2:tuple):
    return (pos1[0] + pos2[0], pos1[1] + pos2[1])

def createWire(pos1:tuple, pos2:tuple):
    return f"w {pos1[0]} {pos1[1]} {pos2[0]} {pos2[1]} 0"

def createResistor(pos1:tuple, pos2:tuple, resistance:float=1000):
    return f"r {pos1[0]} {pos1[1]} {pos2[0]} {pos2[1]} 0 {resistance}"

def createDiode(pos1:tuple, pos2:tuple, type:str="1N5711"):
    return f"d {pos1[0]} {pos1[1]} {pos2[0]} {pos2[1]} 2 {type}"

def createVarVoltRail(pos1:tuple, pos2:tuple, name:str, minVolt:float=0, maxVolt:float=5, curVolt:float=0):
    return f"172 {pos1[0]} {pos1[1]} {pos2[0]} {pos2[1]} 0 7 {curVolt} {maxVolt} {minVolt} 0 0.5 {name}"

def createVoltRail(pos1:tuple, pos2:tuple, curVolt:float=5):
    return f"R {pos1[0]} {pos1[1]} {pos2[0]} {pos2[1]} 0 0 40 {curVolt} 0 0 0.5"

def TranslateComponent(line:str, pos1:tuple):
    par = parse("{:l} {:d} {:d} {:d} {:d} {}",  line)
    return f"{par[0]} {par[1] + pos1[0]} {par[2] + pos1[1]} {par[3] + pos1[0]} {par[4] + pos1[1]} {par[5]}" 

def TransposeTo(circ:str, pos1:tuple):
    return '\n'.join([TranslateComponent(lin, pos1) for lin in circ.split("\n")])

NEURON_TEMPLATE = ""
with open("neurTemplate.txt") as readfile:
    NEURON_TEMPLATE = readfile.read()

ONE_WIRE = 16
TWO_WIRE = 32

class FalNeuron:
    def __init__(self) -> None:
        self.Code = ""
        self.Position = (0,0)
        self.PosInput = (0,0)
        self.NegInput = (0,0)
        self.Output = (0, 0)
        self.PosNum = 0
        self.NegNum = 0
        self.Size = (256, TWO_WIRE * 3)

    def generate(self, pos, addDiode = False) -> None:
        self.Position = (pos[0], pos[1])
        self.PosInput = self.Position
        self.NegInput = add(self.Position, (16, 96))
        self.Code = TransposeTo(NEURON_TEMPLATE, self.Position)
        self.Output = add(self.Position, (256, 48))
        if addDiode:
            old = add(self.Position, (256, 48))
            pen = add(old, (TWO_WIRE, 0))
            self.Code += "\n" + createDiode(old, pen)
            old = pen
            pen = add(old, (ONE_WIRE, 0))
            self.Code += "\n" + createWire(old, pen)
            self.Output = add(self.Output, (ONE_WIRE * 3, 0))
            self.Size = add(self.Size, (48,0))

    def computeNeg(self) -> None:
        offset = 0
        if self.PosNum >= 3:
            offset = (self.PosNum - 3) * TWO_WIRE
            old = self.NegInput
            self.NegInput = add(self.NegInput, (0, offset))
            self.Code += "\n" + createWire(old, self.NegInput)

    def addInput(self, weight, pos1) -> None:
        if weight > 0:
            if self.PosNum > 0:
                old = self.PosInput
                pen = add(old, (0, TWO_WIRE))
                self.Code += "\n" + createWire(old, pen)
                self.PosInput = pen
                if self.PosNum >= 3:
                    # print("+")
                    self.Size = (self.Size[0], self.Size[1] + TWO_WIRE)

            old = self.PosInput
            pen = add(old, (-ONE_WIRE, 0))
            self.Code += "\n" + createWire(old, pen)
            old = pen
            pen = add(old, (-TWO_WIRE, 0))
            self.Code += "\n" + createResistor(old, pen, floor(1000*(1/weight)))
            old = pen
            pen = add(old, (-ONE_WIRE, 0))
            self.Code += "\n" + createWire(old, pen)
            old = pen
            pen = pos1
            self.Code += "\n" + createWire(old, pen)
                
            self.PosNum += 1
        elif weight < 0:
            if self.NegNum > 0:
                old = self.NegInput
                pen = add(old, (0, TWO_WIRE))
                self.Code += "\n" + createWire(old, pen)
                self.NegInput = pen
                # print("-")
                self.Size = (self.Size[0], self.Size[1] + TWO_WIRE)
            old = self.NegInput
            pen = add(old, (-TWO_WIRE, 0))
            self.Code += "\n" + createWire(old, pen)
            old = pen
            pen = add(old, (-TWO_WIRE, 0))
            self.Code += "\n" + createResistor(old, pen, floor(1000*(1/-weight)))
            old = pen
            pen = add(old, (-ONE_WIRE, 0))
            self.Code += "\n" + createWire(old, pen)
            old = pen
            pen = pos1
            self.Code += "\n" + createWire(old, pen)
            self.NegNum += 1

class FalNet:
    def __init__(self) -> None:
        self.Code = ""
        self.PrevConns = []
        self.LayerPos = (0,0)

    def addInput(self, pos) -> None:
        self.PrevConns.append(pos)
    
    def addLayer(self, mat, bias, activation):
        # Neurons = []
        outputs, inputs = mat.shape
        
        useDiode = False
        if activation == "lin":
            useDiode = False
        elif activation == "relu":
            useDiode = True
        
        pen = self.LayerPos
        
        newLayerOut = []
        for i in range(outputs):
            print(i)
            print(bias[i])
            neur = FalNeuron()
            neur.generate(pen, useDiode)
            inpWeight = list(zip(list(mat[i]), range(inputs)))
            print(list(inpWeight))
            negativeWeights = filter(lambda x: x[0] < 0, inpWeight)
            positiveWeights = filter(lambda x: x[0] > 0, inpWeight)

            for weight, conIndex in positiveWeights:
                neur.addInput(weight, self.PrevConns[conIndex])
                print(self.PrevConns[conIndex])
            
            if bias[i] > 0:
                print(neur.PosInput)
                if neur.PosNum == 0:
                    self.Code += "\n" + createVoltRail(add(neur.PosInput, (-ONE_WIRE*5, 0)), add(neur.PosInput, (-ONE_WIRE*6, 0)))
                    neur.addInput(bias[i], add(neur.PosInput, (-ONE_WIRE*5, 0)))
                else:
                    self.Code += "\n" + createVoltRail(add(neur.PosInput, (-ONE_WIRE*5, TWO_WIRE)), add(neur.PosInput, (-ONE_WIRE*6, TWO_WIRE)))
                    neur.addInput(bias[i], add(neur.PosInput, (-ONE_WIRE*5, TWO_WIRE)))

            neur.computeNeg()

            for weight, conIndex in negativeWeights:
                neur.addInput(weight, self.PrevConns[conIndex])
                print(self.PrevConns[conIndex])

            if bias[i] < 0:
                if neur.NegNum == 0:
                    self.Code += "\n" + createVoltRail(add(neur.NegInput, (-ONE_WIRE*5, 0)), add(neur.NegInput, (-ONE_WIRE*6, 0)))
                    neur.addInput(bias[i], add(neur.NegInput, (-ONE_WIRE*5, 0)))
                else:
                    self.Code += "\n" + createVoltRail(add(neur.NegInput, (-ONE_WIRE*5, TWO_WIRE)), add(neur.NegInput, (-ONE_WIRE*6, TWO_WIRE)))
                    neur.addInput(bias[i], add(neur.NegInput, (-ONE_WIRE*5, TWO_WIRE)))

            # Neurons.append(neur)
            newLayerOut.append(neur.Output)
            pen = add(pen, (0, neur.Size[1] + TWO_WIRE))
            self.Code += "\n" + neur.Code
        self.LayerPos = add(self.LayerPos, (neur.Size[0] + TWO_WIRE * 4, 0))
        self.PrevConns = newLayerOut

allCode = ""
allCode += createVarVoltRail((-ONE_WIRE*7, 0), (-ONE_WIRE*9, 0), "x")
allCode += "\n" + createVarVoltRail((-ONE_WIRE*7, ONE_WIRE), (-ONE_WIRE*9, ONE_WIRE), "y")
net = FalNet()
net.addInput((-ONE_WIRE*7, 0))
net.addInput((-ONE_WIRE*7, ONE_WIRE))
net.addLayer(np.array([[-0.7597, -0.4776],[ 0.7230,  0.7230]]), np.array([0.4776, -0.7117]), "relu")
net.addLayer(np.array([[-2.1265, -1.3831]]), np.array([1.0156]), "lin")
# net.addLayer(np.array([[-0.7597, -0.4776]]), np.array([0.4776]), "relu")
# net.addLayer(np.array([[ 0.7230,  0.7230]]), np.array([-0.7117]), "relu")
allCode += "\n" + net.Code

# neur = FalNeuron()
# neur.generate((0,0), True)
# neur.addInput(0.25, (-4*TWO_WIRE,-4*TWO_WIRE))
# neur.addInput(0.33, (-4*TWO_WIRE,-4*TWO_WIRE))
# neur.addInput(0.25, (-4*TWO_WIRE,-4*TWO_WIRE))
# neur.addInput(0.33, (-4*TWO_WIRE,-4*TWO_WIRE))
# neur.addInput(0.75, (-4*TWO_WIRE,-4*TWO_WIRE))
# neur.computeNeg()
# neur.addInput(-0.33, (-4*TWO_WIRE,-4*TWO_WIRE))
# neur.addInput(-0.33, (-4*TWO_WIRE,-4*TWO_WIRE))
# neur.addInput(-0.45, (-4*TWO_WIRE,-4*TWO_WIRE))
# tot = add(neur.Position, neur.Size)
# # neur.Code += "\n" + createWire((-32, tot[1]),(32, tot[1]))
with open("outp.txt", "w") as writefile:
        writefile.write(allCode)