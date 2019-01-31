#!/usr/bin/python

from collections import deque
import re, string, math

class PCB():
	def __init__(self, pid, mem):
		self.pid = pid
		self.filename = ''
		self.memstart = 0
		self.rw = ''
		self.filelen = 0
		self.cpu_usage = 0
		self.cyl = None
		self.cpu_bursts = 0
		self.cpu_accum = 0
		self.memsize = mem
		self.pagetable = []


	def set_attributes(self, filename, memstart, rw, filelen=None, cyl=None):
		self.filename = filename
		self.memstart = memstart
		self.rw = rw
		self.filelen = filelen
		if self.rw=='r': 
			self.filelen=None
		self.cyl = cyl

	def add_usage(self, usage):
		self.cpu_usage += usage
                
	def avg_burst(self):
		if self.cpu_bursts==0: return 0
		else: return (float(self.cpu_accum) / self.cpu_bursts)
		
	def complete_burst(self):
		self.cpu_accum += self.cpu_usage
		self.cpu_usage = 0
		self.cpu_bursts += 1

	def __repr__(self):
		#return '%s%s%s%s%s'%(string.ljust(str(self.pid),8), string.ljust(self.filename,24), string.ljust(str(self.memstart), 9), str.ljust(self.rw, 5), str(self.filelen))
		#if self.cyl==-1: return '%s%s%s%s%s%s%s'%(string.ljust(str(self.pid),8), string.ljust(self.filename,18), string.ljust(str(self.memstart), 9), str.ljust(self.rw, 5), string.ljust(str(self.cpu_accum+self.cpu_usage),9), string.ljust(str(self.avg_burst() ),10), str(self.filelen))
		#else: 
		return '%s%s%s%s%s%s%s%s'%(string.ljust(str(self.pid),8), string.ljust(self.filename,18), string.ljust(str(self.memstart), 9), str.ljust(self.rw, 5), string.ljust(str(self.cpu_accum+self.cpu_usage),9), string.ljust(str(self.avg_burst() ),10), string.ljust(str(self.filelen),12), string.ljust(str(self.cyl),8)   )
		
	def __lt__(self, other):
			return self.cyl < other.cyl

	def __eq__(self, other):
			return self.cyl == other.cyl

	def __le__(self, other):
			return self.cyl < other.cyl or self.cyl == other.cyl

	def __gt__(self, other):
			return not (self.cyl < other.cyl or self.cyl == other.cyl)

	def __ge__(self, other):
			return self.cyl > other.cyl or self.cyl == other.cyl

	def __ne__(self, other):
			return not (self.cyl == other.cyl)
			
	def print_pagetable(self):
		table = '---PID:%d'%(self.pid)
		for page, frame in enumerate(self.pagetable):
			table += '\n%d\t\t%d'%(page,frame)
		return table
				
	table_header = 'Page\t\tFrame'
	attributes_list = 'PID     Filename          Memstart R/W CPU-Time Avg-Burst File-Length Cylinder' # 'PID\tFilename\t\tMemstart R/W  File Length'

def compare_pcb_mem(a, b): #-1 if a comes first
	if b.memsize < a.memsize: return -1
	elif b.memsize > a.memsize: return 1
	else:
		if a.pid < b.pid: return -1
		else: return 1

def words_to_pages(mem, pagesize): #mem:number of words; pagesize: words per page
	return int(math.ceil(1.0*mem / pagesize))

def bits_required(n):
	return len(bin(n-1))-2
	
def hexdigits_required(n):
	return len(hex(n-1))-2
	
class Frame():
	def __init__(self, pid, page):
		self.pid = pid
		self.page = page
	def __repr__(self):
		return "%s%s"%( string.ljust(str(self.pid),8),  string.ljust(str(self.page),8)   )
	
	header = "Frame PID     Page"
		



def input_pos_int(msg = ''):
	out = raw_input(msg)
	while not out.isdigit() or int(out) < 0: out = raw_input(" Input a non-negative integer:")
	return int(out)
	
def input_power_two(msg = ''):
	out = raw_input(msg)
	while not out.isdigit() or int(out) < 0 or not re.search('^0b10*$', bin(int(out)) ): out = raw_input(" Input a non-negative power of 2:")
	return int(out)

def input_hex(msg = ''):
	out = raw_input(msg)
	while not re.search('^[0-9a-fA-F]*$', out ): out = raw_input(" Input a hexadecimal number:")
	return out

#returns true if error
def parse_input(line, system):
	if re.search('^A$',line): return system.arrive()
	elif re.search('^t$',line): return system.exterminate() ###request time
	elif re.search('^S$',line):	return system.snapshot()
	elif re.search('^[pdc]{1}\d+$',line): return system.request( line[0], int(line[1:])-1 ) ###request time; cyl if d
	elif re.search('^[PDC]{1}\d+$',line): return system.complete( line[0], int(line[1:])-1 )
	elif re.search('^T$', line): return system.timer()
	else: return True


class System:

	def __init__(self, p, d, c, s, cyl, mem, page):
		self.devnum = dict()
		self.devnum['p'] = p
		self.devnum['d'] = d
		self.devnum['c'] = c

		self.cyl_count = cyl
		self.slice_length = s

		self.dev = dict()
		for k in self.devnum.keys():
                        if k != 'd':
                                self.dev[k] = []
                                for i in range(self.devnum[k]): self.dev[k].append( deque() )

		self.dev['d'] = []
                for disk in range(self.devnum['d']):
                        self.dev['d'].append( [] )

                self.diskmeta = []
                for disk in self.dev['d']:
                        self.diskmeta.append( 0 ) #head location
			
		self.ready = deque()
		self.pidcount = 0

		self.cpu = None
		
		self.cpu_time = 0
		self.completed = 0
		
		self.memsize = mem
		self.pagesize = page
		
		self.jobpool = []
		self.frametable = []
		for i in range(self.memsize / self.pagesize): self.frametable.append(None)

	def average_cpu(self):
		if self.completed==0: return 0
		else: return float(self.cpu_time)/self.completed
		
	def get_free_frames(self):
		freeframes = []
		for i,frame in enumerate(self.frametable):
			if not frame: freeframes.append(i)
		return freeframes
		
	#pop ready q to cpu
	def shift(self):
		self.jobpool.sort(compare_pcb_mem)
		freespace = self.get_free_frames()
		#print "Freespace:%d"%(len(freespace))
		for i,job in enumerate(self.jobpool):
			if words_to_pages(job.memsize,self.pagesize) <= len(freespace):
				proc = job
				del self.jobpool[i]
				self.ready.append(proc)
				proc.pagetable = []
				for p in range( words_to_pages(proc.memsize, self.pagesize) ): #p = [0, number of pages)
					proc.pagetable.append ( freespace[p] )                    #slot in pagetable gets next frame number listed as free
					self.frametable[freespace[p]] = Frame(proc.pid, p)        #make a frame with pid and number of proc's page
				#print "Proc pagetable:", proc.pagetable, "\tFrametable:", self.frametable
				break
	
		if not self.cpu and len(self.ready)>0: self.cpu = self.ready.popleft()
	
	def arrive(self):
		mem = input_pos_int("Size of process (words):")
		if mem > self.memsize:
			print "Process too large."
			return True
		self.jobpool.append(PCB(self.pidcount,mem))
		self.pidcount += 1
		self.shift()
		return False
		
	def add(self, mem):
		self.jobpool.append(PCB(self.pidcount,mem))
		self.pidcount += 1
		self.shift()
	
	def exterminate(self):
		if not self.cpu: return True
		
		usage = -1
		while not (0 <= usage <= self.slice_length):
			usage = input_pos_int('CPU usage:')
		self.cpu.add_usage(usage)
		
		self.cpu_time += self.cpu.cpu_accum + self.cpu.cpu_usage
		self.completed += 1
		
		print "Exterminated process %s with total usage %dms"%(self.cpu.pid, (self.cpu.cpu_accum + self.cpu.cpu_usage) )

		#free up memory
		for page in self.cpu.pagetable:
			self.frametable[page] = None
		self.cpu = None

		self.shift()

		return False

	def snapshot(self):
		heading = ''
		output = []
		print "Average CPU time for completed processes: %d"%(self.average_cpu() ) 
		cmd = ''
		while not re.search('^[rpdcm]$',cmd): cmd = raw_input('Select r,p,c,d,m:')
		if cmd == 'r':
			heading = 'PID     CPU-Time  Avg-Burst'
			for i in self.ready: output.append( '%s%s%s'%(string.ljust(str(i.pid),8 ), string.ljust(str(i.cpu_accum+i.cpu_usage),10), string.ljust(str(i.avg_burst() ),11) ) )
		elif cmd != 'm':
			heading = PCB.attributes_list
			for n, i in enumerate(self.dev[cmd]):
				output.append ('----%s%d'%(cmd,n+1))
				for j in i: output.append( '%s'%j )
		else:
			heading = Frame.header
			for n,frame in enumerate(self.frametable):
				output.append( string.ljust(str(n),6)  + repr(frame) )
		
		formattedoutput = []
		height = 22
		width = 80
		
		for line in output:
			for i in range(0, len(line), width):
				formattedoutput.append(line[i:i+width])
			
		
		for i in range(0, len(formattedoutput)+1, height):
			print heading
			for line in formattedoutput[i:i+height]: print line
			if i+height <= len(formattedoutput): raw_input("Enter to continue...")
			else: 
				for j in range(  height-(len(formattedoutput)-i)  ): print	
		
		
		
		if cmd != 'm':
			raw_input("Enter to continue...")
			
			
			#print page table###########################################
			output = []
			heading = PCB.table_header
			if cmd == 'r':
				for i in self.ready: 
					for page in i.print_pagetable().splitlines(): 
							output.append( page )
			elif cmd != 'm':
				for n, i in enumerate(self.dev[cmd]):
					#output.append ('----%s%d'%(cmd,n+1))
					for j in i: 
						for page in j.print_pagetable().splitlines(): 
							output.append( page )
			
			formattedoutput = []
			height = 22
			width = 80
		
			for line in output:
				for i in range(0, len(line), width):
					formattedoutput.append(line[i:i+width])
				
			
			for i in range(0, len(formattedoutput)+1, height):
				print heading
				for line in formattedoutput[i:i+height]: print line
				if i+height <= len(formattedoutput): raw_input("Enter to continue...")
				else: 
					for j in range(  height-(len(formattedoutput)-i)  ): print
				
				
			

	def request(self, device, number):
		if number >= self.devnum[device] or not self.cpu: return True
		proc = self.cpu		
		self.cpu = None
		
		usage = -1
		while not (0 <= usage <= self.slice_length):
			usage = input_pos_int('CPU usage:')
		proc.add_usage(usage)
		
		proc.complete_burst()
		
		filename = raw_input('Filename:')
		memstart = None
		while not memstart:
			memstart = self.get_address(input_hex('Memory location:'), proc)
		
		rw = ''
		if device=='p': rw='w'
		while not re.search('^[rw]$', rw): rw = raw_input("Input r(ead) or w(rite):")
		
		filelen=0
		if rw=='w': filelen = input_pos_int("File length:")

                cyl = None
                if device=='d':
                        while not (0 <= cyl < self.cyl_count[number]):
                                cyl = input_pos_int("Cylinder of disk request:")
		
		proc.set_attributes(filename, memstart, rw, filelen, cyl)

		self.dev[device][number].append( proc )
		if device=='d': self.dev['d'][number].sort() #can be optimized by insertion sort
		self.shift()
		return False

	def complete(self, device, number):
		device = device.lower()
		
		if number >= self.devnum[device] or len(self.dev[device][number])<1: return True


		if device != 'd':
				proc = self.dev[device][number].popleft()
				proc.filelength = None
				self.ready.append(proc)
		else:
				self.clook(device,number)
                        
		self.shift()
		return False

	def clook(self, device, number):
		found = False
		for i, request in enumerate(self.dev[device][number]):
				 if self.diskmeta[number] <= request.cyl:
						 found = True
						 break

		if not found:
				i = 0
				self.diskmeta[number] = 0
				request = self.dev[device][number][0]
		
		proc = request
		self.diskmeta[number] = request.cyl + 1
		proc.filelength = None
		proc.cyl=None
		self.ready.append(proc)
		del self.dev[device][number][i]

	def timer(self):
                if not self.cpu: return True
                self.cpu.add_usage(self.slice_length)
                self.ready.append(self.cpu)
                self.cpu = None
                self.shift()
                return False

	def get_address(self, logical_addr, proc): #logical is a hexadecimal string rep of a number; return None if invalid logical address
		pagebits = bits_required( words_to_pages(proc.memsize, self.pagesize) )
		offsetbits = bits_required( self.pagesize )
		framebits = bits_required( len(self.frametable) )
		logicalbits = pagebits + offsetbits
		physicalbits = framebits + offsetbits + (4-(framebits + offsetbits)%4)
		b_logical = (bin( int(logical_addr,base=16) )[2:]).zfill(logicalbits)
		page = int(b_logical[:pagebits], base=2)
		
		#print "pagebits:%d, offsetbits:%d, framebits:%d, logicalbits:%d, physicalbits:%d, page:%d, length:%d"%(pagebits, offsetbits,framebits,logicalbits,physicalbits,page,len(proc.pagetable) )
		
		if page >= len(proc.pagetable): return None #page num out of bounds
		frame = proc.pagetable[page]
		b_frame = bin(frame)[2:].zfill(framebits)
		b_offset = b_logical[pagebits:]
		b_physical = b_frame + b_offset
		physical = (hex( int(b_physical, base=2) )[2:]).zfill(physicalbits/4)
		#print "%s (%s) to (%s) %s"%(logical_addr, b_logical, b_physical, physical)
		return physical
		'''
		pagebits = bits_required( words_to_pages(proc.memsize, self.pagesize) )
		logical = (bin( int(logical_addr,base=16) )[2:]).zfill(4*len(logical_addr)) #logical is binary string
		if pagebits > len(logical):return None #is not valid if not enough bits to rep
		page = int(logical[:pagebits],base=2) #acquire page number
		if page >= len(proc.pagetable): return None #page number is out of bounds
		physical = (bin(proc.pagetable[page])[2:]).zfill(bits_required(len(self.frametable))) + logical[pagebits:] #binary string of physical address
		print "%s (%s) to %s"%(logical_addr, logical, physical)
		physical = hex( int(physical,base=2) )[2:].zfill(hexdigits_required(len(self.frametable))) #hex string of physical address
		return physical
		'''


def main():

	##sysgen
	p = input_pos_int("Number of printer devices:")
	d = input_pos_int("Number of disk devices:")
	c = input_pos_int("Number of CD/RW devices:")
	s = input_pos_int("Length of time slice in ms:")

	cyl = []
	for disk in range(d):
		cyl.append( input_pos_int("Number of cylinders in disk %d:"%(disk+1) ) )
                
    
	page = input_power_two("Size of a page:")
	mem = input_pos_int("Size of memory:")
	while mem % page:
		mem = input_power_two( "Memory should be multiple of page size:")

	tardis = System(p,d,c,s,cyl,mem,page)
	

	##processing
	while(True):
		line = raw_input("#")
		if parse_input(line, tardis): print "Invalid command."


def main2():

	##sysgen
	p = 1
	d = 1
	c = 1
	s = 3

	cyl = []
	for disk in range(d):
		cyl.append( 4 )
                
    
	page = 2
	mem = 100
	while mem % page:
		mem = input_power_two( "Memory should be multiple of page size:")

	tardis = System(p,d,c,s,cyl,mem,page)
	
	
	for i in range(98):
		tardis.add(2)
	##processing
	while(True):
		line = raw_input("#")
		if parse_input(line, tardis): print "Invalid command."

main()