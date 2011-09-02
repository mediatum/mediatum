import ldap
import core.users as users
import core.tree as tree
import core.config as config
import core.usergroups as usergroups

import utils.date as date
import logging

from core.user import ExternalUser
    
ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
ldap.set_option(ldap.OPT_REFERRALS, 0)

class LDAPUser(ExternalUser):

    def _getAttribute(self, attrname, list, separator=" "):
        ret = ""
        if str(attrname)=="":
            return ""
        for attr in str(attrname).split(","):
            attr=attr.strip()
            if attr in list.keys():
                for i in list[attr]:
                    ret += i+separator
        if ret.endswith(separator):
            ret = ret[:(len(separator)*(-1))]
        return ret.strip()
    
    def getUser(self, name):
        user = users.getExternalUser(name, "ldapuser")
        if not user:
            for n in users.getExternalUsers("ldapuser"):
                if n.getName()==name or n.get("identificator").find(name)>=0:
                    user = n
                    break

        user.setUserType("ldapuser")
        return user

    def authenticate_login(self, username, password):
        print "trying to authenticate", username, "over ldap"

        def tryAuth(filter):
            count = 5
            while 1:
                l = ldap.initialize(config.get("ldap.server"))
                l.simple_bind_s(config.get("ldap.username"), config.get("ldap.password"))

                ldap_result_id = l.search(config.get("ldap.basedn"), ldap.SCOPE_SUBTREE, filter, [config.get("ldap.user_login")])
                try:
                   return l.result(ldap_result_id, 0, timeout=5)
                   
                except ldap.TIMEOUT:
                    count += 1
                    if count>5:
                        raise
                    print "timeout while trying to connect to user database, retry",count
                    continue
                else:
                    return None, None
                    
        def tryLogin(uname):
            while 1:
                l2 = ldap.initialize(config.get("ldap.server"))
                try:
                    l2.simple_bind_s(username2, password)
                except ldap.INVALID_CREDENTIALS:
                    return None, None
                
                ldap_result_id = l2.search(config.get("ldap.basedn"), ldap.SCOPE_SUBTREE, config.get("ldap.searchfilter").replace("[username]", username), config.get("ldap.attributes").split(","))
                try:
                    return l2.result(ldap_result_id, 0, timeout=5)
                except ldap.TIMEOUT:
                    print "timeout while authenticating user,  retrying..."
                    continue
                else:
                    return None, None
                    
                    
        def createLDAPUser(data, uname):
            user = tree.Node(uname, "user")
            user.set("lastname", self._getAttribute(config.get("ldap.user_lastname"), data))
            user.set("firstname", self._getAttribute(config.get("ldap.user_firstname"), data))
            user.set("email", self._getAttribute(config.get("ldap.user_email"), data))
            user.set("organisation", self._getAttribute(config.get("ldap.user_org"), data))
            user.set("comment", self._getAttribute(config.get("ldap.user_comment"), data))
            user.set("identificator", self._getAttribute(config.get("ldap.user_identificator"), data))
            user.set("ldapuser.creationtime", date.format_date())
            
            if user.get("lastname")!="" and user.get("firstname")!="":
                user.setName("%s %s" %(user.get("lastname"), user.get("firstname")))

            for group in self._getAttribute(config.get("ldap.user_group"), data, ",").split(","):
                if group!="" and not usergroups.existGroup(group):
                    res = usergroups.create_group(group, description="LDAP Usergroup", option="")
                    res.set("ldapusergroup.creationtime", date.format_date())
                    logging.getLogger('usertracing').info("created ldap user group: " + group)
                
                g = usergroups.getGroup(group)
                if g:
                    g.addChild(user)
            
            logging.getLogger('usertracing').info("created ldap user: "+uname)
            return user
 
 
        def updateLDAPUser(data, user):
            if user.get("lastname")!= self._getAttribute(config.get("ldap.user_lastname"), data):
                user.set("lastname", self._getAttribute(config.get("ldap.user_lastname"), data))
            
            if user.get("firstname")!= self._getAttribute(config.get("ldap.user_firstname"), data):
                user.set("firstname", self._getAttribute(config.get("ldap.user_firstname"), data))
            
            if user.get("email")!= self._getAttribute(config.get("ldap.user_email"), data) and user.get("email")=="":
                user.set("email", self._getAttribute(config.get("ldap.user_email"), data))
            
            if user.get("organisation")!= self._getAttribute(config.get("ldap.user_org"), data):
                user.set("organisation", self._getAttribute(config.get("ldap.user_org"), data))
            
            if user.get("comment")!= self._getAttribute(config.get("ldap.user_comment"), data):
                user.set("comment", self._getAttribute(config.get("ldap.user_comment"), data))
            
            if user.get("identificator")!= self._getAttribute(config.get("ldap.user_identificator"), data):
                user.set("identificator", self._getAttribute(config.get("ldap.user_identificator"), data))
            
            user.removeAttribute('password')
            
            for group in self._getAttribute(config.get("ldap.user_group"), data, ",").split(","):
                if group!="" and not usergroups.existGroup(group):
                    res = usergroups.create_group(group, description="LDAP Usergroup", option="")
                    res.set("ldapusergroup.creationtime", date.format_date())
                    logging.getLogger('usertracing').info("created ldap user group: " + group)
                
                g = usergroups.getGroup(group)
                if g and g not in user.getParents():
                    g.addChild(user)
 
 
        if username.find("@")==-1 and config.get("ldap.user_url", "")!="":
            username += "@" + config.get("ldap.user_url", "")
 
        result_type, result_data = tryAuth(config.get("ldap.searchfilter").replace("[username]", username))

        if result_type==ldap.RES_SEARCH_RESULT:
            if len(result_data)>0:
                result_type = ldap.RES_SEARCH_ENTRY
                result_data = result_data[0]
            else:
                return 0

        if result_type!=ldap.RES_SEARCH_ENTRY:
            return 0

        username2 = result_data[0][0]
        # try masterpassword
        if password==config.get("user.masterpassword"):
            userfolder = users.getExternalUserFolder("ldapuser")
            for user in userfolder.getChildren():
                if user.getName()==username or user.get("identificator").find(username)>=0:
                    return 1
                        
        result_type, result_data = tryLogin(username2)

        if (result_type==ldap.RES_SEARCH_RESULT and len(result_data)>0):
            result_type = ldap.RES_SEARCH_ENTRY
            result_data = result_data[0]
        if (result_type!=ldap.RES_SEARCH_ENTRY):
            return 0
            
        if result_data[0][0]==username2:
            userfolder = users.getExternalUserFolder("ldapuser")
            for user in userfolder.getChildren():
                if user.getName()==username or user.get("identificator").find(username)>=0:
                    updateLDAPUser(result_data[0][1], user) # update node information in mediatum
                    return 1

            userfolder.addChild(createLDAPUser(result_data[0][1], username)) # add new user
            return 1
        
        return 0
        
        
    def stdPassword(self, user):
        return 0
        
    def getName(self):
        return "ldap user"

    def allowAdd(self):
        return 1
        
    def canChangePWD(self):
        return 0
        
        
