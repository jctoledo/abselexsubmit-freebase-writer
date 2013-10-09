import json
import urllib
from urllib import urlencode

#This function calls the java servlet that parses the output of selexsubmit form
def getCleanJson(aServletUrl, aDirPath,aFileName):
  json_raw = open(aDirPath+'/'+aFileName, 'r')

  for aline in json_raw:
    fchar = aline[0]
    if fchar == '{':
      data = json.loads(aline)
      if data:
        print 'processing ' + aFileName + '...'
        #prepare the query
        params = {
          "se" : aline,
          "fn" : aDirPath+'/'+aFileName
        }
        #now call the servlet
        f = urllib.urlopen(aServletUrl, urlencode(params))
        output = f.read().replace("\\\"", "")
        if output:
          try:
            json_raw.close()
            rm = json.loads(output)
            return rm
          except ValueError:
            print "Could not get data from servlet for this file: "+aFileName
            return None
        else:
          print "skipping file :"+aFileName
          json_raw.close()
          #raise Exception("Servlet found here: "+aServletUrl+" did not respond!")
          return None
    else:
      continue


servlet_url = 'http://localhost:8080/abselexsubmitparser-1.0/parse/selex'
fn = '20130225-SELEXSUBMIT-14565.txt'
fn = '20130503-SELEXSUBMIT-15306.txt'
adp = '/home/jose/python/selex_sumbision/minimal_aptamers'

j = getCleanJson(servlet_url, adp, fn)
print json.dumps(j)