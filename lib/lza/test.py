
import lza as lzalib
from lza import LZA, LZAMetadata

# pdf
#filename = "data/testdoc_a.pdf"
#filename = "data/testdoc_encrypt.pdf"
#filename = "data/retro_digitalisierung_eval_050406.pdf"

#filename = "out/out.pdf"

#outputfile = "out/out.pdf"
#outputfile = "out/original.pdf"
########
# tiff
#filename = "data/test.tiff"
#filename = "data/test_2.tiff"

#filename = "out/out.tiff"

#outputfile = "out/out.tiff"
#outputfile = "out/original.tiff"
########
# jpeg  
#filename="data/test.jpg"  
#filename = "data/test_com.jpg"

filename = "out/out.jpg"

#outputfile = "out/out.jpg"
outputfile = "out/original.jpg"

from utils import readInfo
metadata = LZAMetadata(readInfo())

############################################
lza = LZA(filename)

#lza.writeMediatumData(metadata, outputfile)

#print lza.getMediatumData()


lza.getOriginal(outputfile)





