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
        user.setUserType("ldapuser")
        return user

    def authenticate_login(self, username, password):
        print "trying to authenticate", username, "over ldap"
        count = 5

        while 1:
            l = ldap.initialize(config.get("ldap.server"))
            l.simple_bind_s(config.get("ldap.username"), config.get("ldap.password"))

            ldap_result_id = l.search(config.get("ldap.basedn"), ldap.SCOPE_SUBTREE, config.get("ldap.searchfilter").replace("[username]", username), [config.get("ldap.user_login")])
            try:
               result_type, result_data = l.result(ldap_result_id, 0, timeout=5)
            except ldap.TIMEOUT:
                count = count + 1
                if count>5:
                    raise
                print "timeout while trying to connect to user database, retry",count
                continue
            else:
                break
        
        if result_type==ldap.RES_SEARCH_RESULT:
            if len(result_data)>0:
                result_type = ldap.RES_SEARCH_ENTRY
                result_data = result_data[0]
            else:
                print "user", username, "not found in ldap"
                return 0

        if result_type!=ldap.RES_SEARCH_ENTRY:
            #for a in ['RES_ADD', 'RES_ANY', 'RES_BIND', 'RES_COMPARE', 'RES_DELETE', 'RES_EXTENDED', 'RES_MODIFY', 'RES_MODRDN', 'RES_SEARCH_ENTRY', 'RES_SEARCH_REFERENCE', 'RES_SEARCH_RESULT', 'RES_UNSOLICITED']:
            #    print a,eval('ldap.'+a)
            print "result_type is", result_type, "should be ldap.RES_SEARCH_ENTRY =", ldap.RES_SEARCH_ENTRY
            return 0

        username2 = result_data[0][0]
        
        while 1:
            l2 = ldap.initialize(config.get("ldap.server"))
            try:
                l2.simple_bind_s(username2, password)
            except ldap.INVALID_CREDENTIALS:
                print "bad password (1)"
                return 0
            
            ldap_result_id = l2.search(config.get("ldap.basedn"), ldap.SCOPE_SUBTREE, config.get("ldap.searchfilter").replace("[username]", username), config.get("ldap.attributes").split(","))
            #searchFilter = "authLogin="+username

            ldap_result_id = l2.search(config.get("ldap.basedn"), ldap.SCOPE_SUBTREE, config.get("ldap.searchfilter").replace("[username]", username), config.get("ldap.attributes").split(","))
            try:
                result_type, result_data = l2.result(ldap_result_id, 0, timeout=5)
            except ldap.TIMEOUT:
                print "timeout while authenticating user,  retrying..."
                continue
            else:
                break

        if (result_type==ldap.RES_SEARCH_RESULT and len(result_data)>0):
            result_type = ldap.RES_SEARCH_ENTRY
            result_data = result_data[0]
        if (result_type!=ldap.RES_SEARCH_ENTRY):
            print "bad password (2)"
            return 0
        if result_data[0][0]==username2:
            userfolder = users.getExternalUserFolder("ldapuser")
            for user in userfolder.getChildren():
                if user.getName()==username:
                    return 1
            user = tree.Node(username, "user")
            user.setPassword(password)
            user.set("lastname", self._getAttribute(config.get("ldap.user_lastname"), result_data[0][1]))
            user.set("firstname", self._getAttribute(config.get("ldap.user_firstname"), result_data[0][1]))
            user.set("email", self._getAttribute(config.get("ldap.user_email"), result_data[0][1]))
            user.set("organisation", self._getAttribute(config.get("ldap.user_org"), result_data[0][1]))
            user.set("comment", self._getAttribute(config.get("ldap.user_comment"), result_data[0][1]))
            
            user.set("ldapuser.creationtime", date.format_date())
            logging.getLogger('usertracing').info("created ldap user: "+username)
            
            groups = self._getAttribute(config.get("ldap.user_group"), result_data[0][1], ",").split(",")
            for group in groups:
                if group!=""and not usergroups.existGroup(group):
                    res=usergroups.create_group(group, description="LDAP Usergroup", option="")
                    res.set("ldapusergroup.creationtime", date.format_date())
                    logging.getLogger('usertracing').info("created ldap user group: "+group)
                    
                g = usergroups.getGroup(group)
                if g:
                    g.addChild(user)

            userfolder.addChild(user)
            return 1
        print "bad password (3)"
        return 0
        
    def stdPassword(self, user):
        return 0
        
    def getName(self):
        return "ldap user"

    def allowAdd(self):
        return 0
        
