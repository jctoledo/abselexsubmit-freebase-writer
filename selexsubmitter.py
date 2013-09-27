# -*- coding: utf-8 -*-
# Copyright (c) 2013 Jose Cruz-Toledo

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

#
# Copyright (C) 2013 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Command-line skeleton application for Freebase API.
Usage:
  $ python selexsubmitter.py

You can also get help on all the command-line flags the program understands
by running:

  $ python selexsubmitter.py --help

"""

import argparse
import httplib2
import os
import sys
import json
import urllib
import os.path

from urllib import urlencode
from apiclient import discovery
from oauth2client import file
from oauth2client import client
from oauth2client import tools

# Parser for command-line arguments.
parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    parents=[tools.argparser])
parser.add_argument('-su', '--servlet_url', help='the URL of the servlet that parses the JSON files', required=True)
parser.add_argument('-dir', '--input_directory', help='the local directory that has the input JSON files', required=True)

# CLIENT_SECRETS is name of a file containing the OAuth 2.0 information for this
# application, including client_id and client_secret. You can see the Client ID
# and Client secret on the APIs page in the Cloud Console:
# <https://cloud.google.com/console#/project/1083819269171/apiui>
CLIENT_SECRETS = os.path.join(os.path.dirname(__file__), 'client_secrets.json')

# Set up a Flow object to be used for authentication.
# Add one or more of the following scopes. PLEASE ONLY ADD THE SCOPES YOU
# NEED. For more information on using scopes please see
# <https://developers.google.com/+/best-practices>.
FLOW = client.flow_from_clientsecrets(CLIENT_SECRETS,
  scope=[
      'https://www.googleapis.com/auth/freebase',
    ],
    message=tools.message_if_missing(CLIENT_SECRETS))


def main(argv):
  # Parse the command-line flags.
  flags = parser.parse_args(argv[1:])
  #define some vars 
  service_url_write = 'https://www.googleapis.com/freebase/v1sandbox/mqlwrite'
  inputFilesPath = flags.input_directory
  servlet_url = flags.servlet_url

  # If the credentials don't exist or are invalid run through the native client
  # flow. The Storage object will ensure that if successful the good
  # credentials will get written back to the file.
  storage = file.Storage('sample.dat')
  credentials = storage.get()
  if credentials is None or credentials.invalid:
    credentials = tools.run_flow(FLOW, storage, flags)

  # Create an httplib2.Http object to handle our HTTP requests and authorize it
  # with our good Credentials.
  http = httplib2.Http()
  http = credentials.authorize(http)
  # Construct the service object for the interacting with the Freebase API.
  service = discovery.build('freebase', 'v1', http=http)
  #get a list of all of the input files
  cleanJson = getCleanJson(servlet_url, inputFilesPath)
  #now prepare a write query for the cleanJSON
  writeQuery = writeToFreebase(cleanJson, service_url_write, http, credentials)

#Creates an empty selex experiment topic
#creates the corresponding topics:
# partitioning method, recovery methods and selex conditions
def createSelexExperimentTopic(aServiceUrl, anHttp, someCredentials):
  #1: create a selex experiment topic
  q = {
    "create" :"unconditional",
    "mid" : None,
    "type" : "/base/aptamer/selex_experiment",
    "b:type" : "/base/aptamer/experiment",
    "c:type" : "/base/aptamer/interaction_experiment",
  }
  params = makeRequestBody(someCredentials, q)
  se_mid = runWriteQuery(params, aServiceUrl, anHttp)
  if se_mid:
    #now create the partitioning and recovery methods and attach them 
    #to the selex experiment topic created earlier
    #create a partitioning method topic
    q = {
      "create" :"unconditional",
      "mid":None,
      "type":"/base/aptamer/partitioning_method",
      "/base/aptamer/partitioning_method/is_partitioning_method_of":{"connect":"insert", "mid":se_mid}
    }
    params = makeRequestBody(someCredentials, q)
    pm_mid = runWriteQuery(params, aServiceUrl, anHttp)
    #create a recovery method topic
    q = {
      "create":"unconditional", "mid":None, 
      "type":"/base/aptamer/recovery_method_se",
      "/base/aptamer/recovery_method_se/is_recovery_method_of":{"connect":"insert", "mid":se_mid}
    }
    params = makeRequestBody(someCredentials, q)
    rm_mid = runWriteQuery(params, aServiceUrl, anHttp)
    #create an empty selex condition topic
    q = {
      "create":"unconditional", "mid":None,
      "type":"/base/aptamer/selex_conditions",
      "b:type": "/base/aptamer/experimental_conditions",
      "/base/aptamer/experimental_conditions/are_experimental_conditions_of":{"connect":"insert", "mid":se_mid}
    }
    params = makeRequestBody(someCredentials, q)
    sc_mid = runWriteQuery(params, aServiceUrl, anHttp)
    if sc_mid:
      #create a selection solution and attach it to the selex conditions topic
      q = {
        "create":"unconditional", "mid":None, 
        "type":"/base/aptamer/selection_solution",
        "/base/aptamer/selection_solution/is_selection_solution_of_sc":{"connect":"insert", "mid":sc_mid}
      }
      params = makeRequestBody(someCredentials, q)
      ss_mid = runWriteQuery(params, aServiceUrl, anHttp)
      if not ss_mid:
        raise Exception ("Could not create selection solution!")
        sys.exit()
    else:
      raise Exception("Could not create selex conditions!")
      sys.exit()
    
    return se_mid
  else:
    raise Exception("Could not create Selex experiment topic!")
    return None;

def makeRequestBody(someCredentials, aQuery):
  p ={
    'oauth_token': someCredentials.access_token,
    'query': json.dumps(aQuery)
  }
  return p
     

def writeAQuery(someCredential, aquery):
  try:
    params = {
      'oauth_token': someCredential.access_token,
      'query': json.dumps(aquery)
    }
    url = service_url_write + '?' + urllib.urlencode(params)
    resp, content = http.request(url)
    return resp, content

  except client.AccessTokenRefreshError:
    print ("The credentials have been revoked or expired, please re-run"
      "the application to re-authorize")

def runWriteQuery(someParams, aServiceUrl, anHttp):
  url = aServiceUrl+'?'+urllib.urlencode(someParams)
  resp, content = anHttp.request(url)
  if resp["status"] == '200':
    #everything worked
    r = json.loads(content)
    return r["result"]["mid"]
  else:
    print resp
    print content
    raise Exception("Could not run query!! erno:234442")
    sys.exit()
    return None

def writeToFreebase(cleanJson, aServiceUrl, anHttp, someCredentials):
  #create an empty selex experiment topic and get its mid
  mid = createSelexExperimentTopic(aServiceUrl, anHttp, someCredentials)
  #add the pmid if available
  try:
    pmid = cleanJson["se"]["pmid"]
    pmid = 12345
    q = {
      "mid":mid,
      "/base/aptamer/experiment/pubmed_id":{
        "connect":"insert",
        "value":str(pmid)
      }
    }
    params = makeRequestBody(someCredentials, q)
    x = runWriteQuery(params, aServiceUrl, anHttp) 
    if x == None:
      print "Could not add pmid errno: 234"
      sys.exit()
  except KeyError :
    pass
  #try to add the bibiographic reference
  try:
    ref = cleanJson["se"]["reference"]
    q = {
      "mid":mid,
      "/base/aptamer/experiment/has_bibliographic_reference":{
        "connect" : "insert",
        "value": ref
      }
    }
    params = makeRequestBody(someCredentials, q)
    if runWriteQuery(p, aServiceUrl, anHttp) == None:
      print "Could not add reference errno: 4353"
      sys.exit()
  except KeyError:
    pass
  #try doi
  try:
    doi = cleanJson["se"]["doi"]
    q = {
      "mid":mid,
      "/base/aptamer/experiment/digital_object_identifier":{
        "connect" : "insert",
        "value": doi
      }
    }
    params = makeRequestBody(someCredentials, q)
    if runWriteQuery(params, aServiceUrl, anHttp) == None:
      print "Could not add reference errno: 4353"
      sys.exit()
  except KeyError:
    pass
  
  print mid
  return mid
  
#This function calls the java servlet that parses the output of selexsubmit form
def getCleanJson(aServletUrl, aFilePath):
  for fn in os.listdir(aFilePath):
    json_raw = open(aFilePath+'/'+fn, 'r')
    for aline in json_raw:
      fchar = aline[0]
      if fchar == '{':
        data = json.loads(aline)
        if data:
          print 'processing ' + fn + '...'
          #prepare the query
          params = {
            "se" : aline,
            "fn" : aFilePath
          }
          #now call the servlet
          f = urllib.urlopen(aServletUrl, urlencode(params))
          output = f.read().replace("\\\"", "")
          if output:
            json_raw.close()
            rm = json.loads(output)
            return rm
          else:
            json_raw.close()
            raise Exception("Servlet found here: "+aServletUrl+" did not respond!")
            return None
      else:
        continue

if __name__ == '__main__':
  main(sys.argv)
