from string import whitespace

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
    minx = 99999999999
    miny = 99999999999
    maxx = -9999999999
    maxy = -9999999999
    graphicLines = findSectionExhaustive("kicad_pcb.gr_line", parseTree)
    for line in graphicLines[0]:
        if findSectionExclusive("layer", line)[1][0] != "Edge.Cuts":
            continue
        start = findSectionExclusive("start", line)
        end = findSectionExclusive("end", line)
        #print start, end
        minx = float(min(minx, float(start[1]), float(end[1])))
        miny = float(min(miny, float(start[2]), float(end[2])))
        maxx = float(max(maxx, float(start[1]), float(end[1])))
        maxy = float(max(maxy, float(start[2]), float(end[2])))
    return round(minx, 2), round(miny, 2), round(maxx, 2), round(maxy, 2), round(abs(minx-maxx), 2), round(abs(maxy-miny), 2)


def findSmallestTrace(parseTree):
    traces = findSectionExhaustive("kicad_pcb.segment", parseTree)
    minTraceWidth = 99999999999
    for trace in traces[0]:
        minTraceWidth = min(minTraceWidth, float(findSectionExclusive("width", trace)[1]))
    return minTraceWidth

if __name__ == "__main__":
    import sys

    with open(sys.argv[1], 'r') as myfile:
        data = myfile.read()
        p = parse(data)
        #print p
        print "file made with Kicad " + findSectionExclusive("kicad_pcb.version", p)[1] + ".x"
        print "\t Board thickness " + findSectionExclusive("kicad_pcb.general.thickness", p)[1] + "mm"
        print "\t Smallest Trace is " + str(findSmallestTrace(p)) + "mm"
        print calcBounds(p)
