#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* -- commands
 *
*/


int showHelp () {
    char help[4096] = "\ncrmctl: simple cluster management tool\n"
                      "\nCommands:\n"
                      "\n  State Overview:"
                      "\n    crmctl state"
                      "\n\n  Locate:\n"
                      "    locate <resource>\n    locate master <resource>\n"
                      "\n  Manage:\n"
                      "    clean <resource> [ <node> ]\n\n    ban <resource> <node>\n    unban <resource> <node>\n\n"
                      "    disable <resoource>\n    enable <resource> \n\n  Failover:\n    failover <resource>\n"
                      "\n  Query:"
                      "\n    nodes [ ips ]\n    resources [ brief ]\n    config\n    constraints\n    properties\n";

    printf("%s", help);
    return 0;

}

/* --- find where a resource is running--- */
int locateResource (char *resource)
{
    // replaces: pcs resource --full | grep $RESOURCE
    char cmd[1024];
    snprintf(cmd, sizeof(cmd), "crm_resource --locate --resource %s", resource);
    return system(cmd);
}

int locateResourceMaster (char *resource)
{
    // replaces: pcs status --full | grep Master | grep $RESOURCE
    char cmd[1024];
    snprintf(cmd, sizeof(cmd), "crm_resource --locate --resource %s --master", resource);
    return system(cmd);
}

/* --- ban / clear --- */
int banResourceOnNode (char *resource, char *node)
{
    // replaces: pcs resource ban $RESOURCE $NODE
    char cmd[1024];
    snprintf(cmd, sizeof(cmd), "crm_resource --resource %s --ban --node %s --quiet", resource, node);
    return system(cmd);
}

int unbanResourceOnNode (char *resource, char *node )
{
    // replaces: pcs resource cleanup $RESOURCE $NODE
    char cmd[1024];
    snprintf(cmd, sizeof(cmd), "crm_resource --resource %s --clear --node %s --quiet", resource, node);
    return system(cmd);
}

/* --- pcs cleanup replacement --- */
int cleanResourceOnNode (char *resource, char *node)
{
    // replaces: pcs resource cleanup $RESOURCE $NODE
    char cmd[1024];
    snprintf(cmd, sizeof(cmd), "crm_resource --resource %s --cleanup --node %s --force --quiet", resource, node);
    return system(cmd);
}

int cleanResource (char *resource, int force)
{
    // replaces: pcs resource cleanup $RESOURCE
    char cmd[1024];
    char force_cmd[1024];
    if (force == 1)
    {
        strcpy(force_cmd, "--force");
    } else
    {
        strcpy(force_cmd, "");
    }
    snprintf(cmd, sizeof(cmd), "crm_resource --resource %s --cleanup %s --quiet", resource, force_cmd);
    return system(cmd);
}

/* --- enable, disable resource --- */
int enableResource (char *resource, int start)
{
    // replaces: pcs resource enable  [ --start ]
    char cmd[1024];
    if (start == 1)
    {
        snprintf(cmd, sizeof(cmd), "pcs resource enable %s --start", resource);
    }
    else
    {
        snprintf(cmd, sizeof(cmd), "pcs resource enable %s", resource);
    }
    return system(cmd);
}

int disableResource ( char *resource, int force)
{
    // replaces: pcs resource disable [ --force ]
    char cmd[1024];
    if (force == 1)
    {
        snprintf(cmd, sizeof(cmd), "pcs resource disable %s", resource);
    }
    else
    {
        snprintf(cmd, sizeof(cmd), "pcs resource disable %s --force", resource);
    }
    return system(cmd);
}

/* failover resource */
int failoverResource ( char *resource )
{
    // replaces: /usr/local/eptt/bin/failover.sh RESOURCE INT INT INT INT
    char cmd[1024];
    snprintf(cmd, sizeof(cmd), "/usr/local/eptt/bin/monitored-failover.sh -t %s -m", resource);
    return system(cmd);
}

int moveResource (char *resource )
{
    printf("Can't move resource - not implemented!");
    return 127;
}

/* get overviews, statii, etc */
int getNodes ()
{
    // replaces: pcs status --full | grep Online | cut -d '[' -f 2 | cut -d ']' -f 1 | xargs
    return system("crm_node --list | xargs");
}

int getNodeHosts ()
{
    // replaces: ?
    char cmd[2048] = "cat /etc/hosts | grep -v localhost | grep -v '::' | grep -v 172 | cut -d ' ' -f 1,2 | grep -E 'ptt.*|priv.*|web'";
    return system(cmd);
}

int getResources( int brief)
{
    if (brief == 1)
    {

        // replaces: pcs resource show $RESOURCES
        return system("crm_resource --list-raw | cut -d ':' -f 1 | sort -u");
    }
    else
    {
        // replaces: pcs resource show --full
        return system("crm_resource --list-raw");
    }
}

int getState ()
{
    //replaces: pcs status --full
    return system("crm_mon --one-shot --show-detail");
}

int getConfig ()
{
    return system("pcs config --full");
}

int getProperties ()
{
    return system("pcs property show --full");
}

int getAllConstraints ()
{
    //replaces: pcs constraint show --full
    return system("crm_mon --neg-locations --show-detail --one-shot");
}

int getBlame () {
    /* TODO: remove this */
    printf("\ncrmctl v1.0\nIf this is broken, blame James #4\n");
    return 1;
}
int main(int argc, char *argv[])
{
    /* Commands are evaluated and executed in the following order:
     * - [ missing argv[1] ]
     * - state
     * - nodes
     * - resources
     * - constraints
     * - config
     * - blame
     * - properties
     * - locate
     * - ban
     * - unban
     * - clean
     * - disable
     * - enable
     * - failover
     * - [ invalid argv[1], have[ argv[2,3,4] ]]
     *
     * Exit code is 0 for success, 1 for failure.
     *
     */

    // Will be our return code.
    unsigned int r;

    if (argc == 1)
    {
        showHelp();
        printf("\nFATAL: At least one argument is required!\n");
        return 1;
    }

    /* Process args */

    // STATE
    if (strcmp(argv[1], "state") == 0)
    {
        r = getState();
    }
        // NODES
    else if (strcmp(argv[1], "nodes") == 0)
    {
        if (argc == 2)
        {
            r = getNodes();
        } else if (argc == 3)
        {
            r = getNodeHosts();
        } else
        {
            printf("Fatal: invalid arg passed to: crmctl nodes [ ips ]\n");
            return 1;
        }
    }
        // RESOURCES
    else if (strcmp(argv[1], "resources") == 0)
    {
        if (argc == 3)
        {
            if (strcmp(argv[2], "brief") == 0)
            {
                r = getResources(1);
            }
        }
        else
        {
                r = getResources(0);
        }
    }
        // CONSTRAINTS
    else if (strcmp(argv[1], "constraints") == 0)
    {
        r = getAllConstraints();
    }
        // CONFIG
    else if (strcmp(argv[1], "config") == 0)
    {
        r = getConfig();
    }
        // BLAME
    else if (strcmp(argv[1], "blame") == 0)
    {
        r = getBlame();
    }
        // PROPERTIES
    else if (strcmp(argv[1], "properties") == 0)
    {
        r = getProperties();
    }
        // LOCATE | FIND
    else if ((strcmp(argv[1], "locate") == 0) || (strcmp(argv[1], "find") == 0))
    {
        if (strcmp(argv[2], "master") == 0)
        {
            printf("Locate Master");
            r = locateResourceMaster(argv[2]);
        } else
        {
            printf("Locate Resource");
            r = locateResource(argv[2]);
        }
    }
        // BAN
    else if (strcmp(argv[1], "ban") == 0 && strcmp(argv[3], "") != 0)
    {
        printf("BAN\n");
        r = banResourceOnNode(argv[2], argv[3]);
    }
        // UNBAN/CLEAR
    else if (strcmp(argv[1], "unban") == 0 && strcmp(argv[3], "") != 0)
    {
        printf("Unban\n");
        r = unbanResourceOnNode(argv[2], argv[3]);
    }
        // CLEAN
    else if (strcmp(argv[1], "clean") == 0)
    {
        if (argc == 4)
        {
            printf("Cleanup %s on %s\n", argv[2], argv[3]);
            r = cleanResourceOnNode(argv[2], argv[3]);
        } else if (argc == 3)
        {
            printf("Cleanup %s\n", argv[2]);
            r = cleanResource(argv[2], 1);
        } else
        {
            printf("crmctl cleanup <resource> [ <NODE> ]\nFatal: invalid usage\n");
            r = 1;
        }
    }
        // DISABLE
    else if (strcmp(argv[1], "disable") == 0 && strcmp(argv[2], "") != 0)
    {
        printf("Disable %s\n", argv[2]);
        r = disableResource(argv[2], 1);
    }
        // ENABLE
    else if (strcmp(argv[1], "enable") == 0 && strcmp(argv[2], "") != 0)
    {
        printf("Enable %s\n", argv[2]);
        r = enableResource(argv[2], 1);
    }
        // FAILOVER
    else if (strcmp(argv[1], "failover") == 0 && strcmp(argv[2], "") != 0)
    {
        printf("Failover resource: %s\n", argv[2]);
        r = failoverResource(argv[2]);
    }
        // HELP
    else if (strcmp(argv[1], "help") == 0)
    {
        r = showHelp();
    }
        // BAD SECONDARY INPUT
    else
    {
        /* if we dont have an action (first arg), then it is caught at top */
        if (argc == 2)
        {
            showHelp();
            printf("\nFATAL: invalid action %s\n", argv[1]);
        } else if (argc == 3)
        {
            showHelp();
            printf("FATAL: Bad command or substitution: %s -> %s\n", argv[1], argv[2]);
        } else
        {
            printf("FATAL: Bad or unknown command provided.\n");
        }
        r = 1;
    }
    return r;
}
