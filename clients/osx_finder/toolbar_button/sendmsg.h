#ifndef __SEND_MSG_SCPLUGIN__
#define __SEND_MSG_SCPLUGIN__


enum MenuItems
{
    ADD = 1,
    ANNOTATE, 
    CHECK_FOR_MODS,
    CHECKOUT,
    CLEANUP,
    COMMIT,
    DELETE,
    EXPORT,
    DIFF_RAW,
    DIFF_GUI,
    IGNORE,
    LOG,
    MARK_RESOLVED,
    PROPERTIES,
    REVERT,
    RENAME,
    UPDATE,
    UPDATE_TO,
    BRANCH,
    MERGE,
    RELOCATE,
    REPO_BROWSER,
    SWITCH,
    LOCK,
    UNLOCK,
    CREATE_PATCH,
    APPLY_PATCH,
    SETTINGS,
    ABOUT
};


void sendCommand(NSArray* selectedFiles, int cmd);

#endif