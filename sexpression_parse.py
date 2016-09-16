from string import whitespace
import math
atom_end = set('()"\'') | set(whitespace)

#credit: mostly from https://gist.github.com/pib/240957
def parse(sexp):
    stack, i, length = [[]], 0, len(sexp)
    while i < length:
        c = sexp[i]

        #print c, stack
        reading = type(stack[-1])
        if reading == list:
            if   c == '(': stack.append([])
            elif c == ')':
                stack[-2].append(stack.pop())
                if stack[-1][0] == ('quote',): stack[-2].append(stack.pop())
            elif c == '"': stack.append('')
            elif c == "'": stack.append([('quote',)])
            elif c in whitespace: pass
            else: stack.append((c,))
        elif reading == str:
            if   c == '"':
                stack[-2].append(stack.pop())
                if stack[-1][0] == ('quote',): stack[-2].append(stack.pop())
            elif c == '\\':
                i += 1
                stack[-1] += sexp[i]
            else: stack[-1] += c
        elif reading == tuple:
            if c in atom_end:
                atom = stack.pop()
                if atom[0][0].isdigit(): stack[-1].append(atom[0])
                else: stack[-1].append(atom)
                if stack[-1][0] == ('quote',): stack[-2].append(stack.pop())
                continue
            else: stack[-1] = ((stack[-1][0] + c),)
        i += 1
    return stack.pop()


#Returns the first match.
def findSectionExclusive(searchTerm, parseTree):
    spl = searchTerm.split(".")
    name = spl[0]
    futureTerm = searchTerm[len(name)+1:]
    if name == "":
        return parseTree

    for element in parseTree:
        if type(element) == list and len(element) > 0:
            first = element[0]
            if type(first) == tuple and first[0] == name:
                return findSectionExclusive(futureTerm, element)


#returns a list of multiple matches if there are some.
def findSectionExhaustive(searchTerm, parseTree):
    spl = searchTerm.split(".")
    name = spl[0]
    futureTerm = searchTerm[len(name)+1:]
    #print searchTerm, futureTerm, name
    if name == "":
        return parseTree

    output = []
    for element in parseTree:
        if type(element) == list and len(element) > 0:
            first = element[0]
            if type(first) == tuple and first[0] == name:
                output.append(findSectionExhaustive(futureTerm, element))
    return output

def calcBounds(parseTree):
    area = findSectionExclusive("kicad_pcb.general.area", p)
    minx = float(area[1])
    miny = float(area[2])
    maxx = float(area[3])
    maxy = float(area[4])

    return round(minx, 2), round(miny, 2), round(maxx, 2), round(maxy, 2), round(abs(minx-maxx), 2), round(abs(maxy-miny), 2)

def findSmallestClearance(parseTree):
    nets = findSectionExhaustive("kicad_pcb.net_class", parseTree)
    netNameToClearance = dict()
    for net in nets[0]:
        netNameToClearance[net[1]] = float(findSectionExclusive("clearance", net)[1])
    minClearance = 99999999999
    smallestKey = "No clearances specified"
    for key in netNameToClearance.keys():
        if netNameToClearance[key] < minClearance:
            smallestKey = key[0]
            minClearance = netNameToClearance[key]
    return minClearance, smallestKey

def findSmallestTrace(parseTree):
    traces = findSectionExhaustive("kicad_pcb.segment", parseTree)
    minTraceWidth = 99999999999
    for trace in traces[0]:
        minTraceWidth = min(minTraceWidth, float(findSectionExclusive("width", trace)[1]))
    if minTraceWidth == 99999999999:
        return None
    return minTraceWidth

def findSmallestAnnularRing(parseTree):
    vias = findSectionExhaustive("kicad_pcb.via", parseTree)
    minAnnularRingSize = 99999999999
    for via in vias[0]:
        minAnnularRingSize = min(minAnnularRingSize, float(findSectionExclusive("size", via)[1]) - float(findSectionExclusive("drill", via)[1]))
    if minAnnularRingSize == 99999999999:
        return None
    return minAnnularRingSize

def findSmallestDrill(parseTree):
    vias = findSectionExhaustive("kicad_pcb.via", parseTree)
    minDrillSize = 99999999999
    for via in vias[0]:
        minDrillSize = min(minDrillSize, float(findSectionExclusive("drill", via)[1]))
    modules = findSectionExhaustive("kicad_pcb.module", parseTree)
    for module in modules[0]:
        pads = findSectionExhaustive("pad", module)
        for pad in pads:
            drill = findSectionExclusive("drill", pad)
            if drill:
                minDrillSize = min(minDrillSize, float(drill[1]))
    if minDrillSize == 99999999999:
        return None
    return minDrillSize


if __name__ == "__main__":
    import sys, os

    if len(sys.argv) < 2:
        print "USAGE: kicad2pcbshopper <path-to-kicad_pcb-file.>"
        os.exit(1)

    if not sys.argv[1].endswith(".kicad_pcb"):
        print "You must give the path to a .kicad_pcb file! if KiCad is giving you some other format (such as .brd) you are running an archaic version an should update to the latest stable!"
        os.exit(1)

    with open(sys.argv[1], 'r') as myfile:
        data = myfile.read()
        p = parse(data)
        #print p
        kicadVersion = findSectionExclusive("kicad_pcb.version", p)[1]
        smallestTrace = findSmallestTrace(p)
        smallestDrill = findSmallestDrill(p)
        smallestAnnularRing = findSmallestAnnularRing(p)
        boardThickness = findSectionExclusive("kicad_pcb.general.thickness", p)[1]
        startx, starty, endx, endy, width, height = calcBounds(p)
        clearance = findSmallestClearance(p)

        print "File made with Kicad " + kicadVersion + ".x"
        print "\t Board thickness " + boardThickness + "mm"

        if not smallestTrace:
            print "\t Could not find any traces on the board. (WARN: Smallest trace unspecified)"
        else:
            print "\t Smallest Trace is " + str(smallestTrace) + "mm"
        if not smallestDrill:
            print "\t Could not find any vias or drills on the board. (WARN: Smallest drill unspecified)"
        else:
            print "\t Smallest Drill is " + str(smallestDrill) + "mm"
        if not smallestAnnularRing:
            print "\t Could not find any vias on the board. (WARN: Annular ring size unspecified)"
        else:
            print "\t Smallest Annular Ring is " + str(smallestAnnularRing) + "mm."
        print "\t Smallest trace clearance is " + str(clearance[0]) + "mm. ('" + str(clearance[1]) + "' net class)"
        print "\t Start point is (" + str(startx) + "," + str(starty) + ")"
        print "\t width = " + str(width) + "mm, height = " + str(height) + "mm"

        print ""
        print "Please make sure your board has no DRC errors before trusting this tool."
