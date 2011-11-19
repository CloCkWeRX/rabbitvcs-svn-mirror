#import "fileListBuilder.h"

// Applescript to get what is currently selected in the Finder
static const char* appleScript = 
"property stdout : \"\"\n"

"tell application \"Finder\"\n"

    "copy selection to selectedItems\n"
    "set stdout to \"\"\n"

    "if ((count of selectedItems) > 0) then\n"
        "repeat with x in selectedItems\n"
            "set itemN to (POSIX path of (x as alias))\n"
            "set stdout to stdout & itemN & \"\n"
            "\"\n"
        "end repeat\n"
    "else\n"
        "set theWindow to window 1\n"
        "set thePath to (POSIX path of (target of theWindow as alias))\n"
        "set stdout to thePath\n"
    "end if\n"

    "stdout\n"

"end tell";

NSAppleScript* scriptObject = nil;

void compileScript()
{
    NSDictionary* errorDict;
    
    scriptObject = [[NSAppleScript alloc] initWithSource:
                                    [NSString stringWithUTF8String:appleScript]];
    
    if(![scriptObject compileAndReturnError: &errorDict])
    {
        fprintf(stderr, "Failed to compile appleScript!\n");
        scriptObject = nil;
    }
    
}

NSArray* getSelectedFilesList()
{
    //printf("Running script : \n %s", appleScript);
    
    NSAppleEventDescriptor* returnDescriptor = NULL;
    NSDictionary* errorDict;

    if (scriptObject == nil)
    {
        compileScript();
        if (scriptObject == nil)  return nil;
    }
    
    returnDescriptor = [scriptObject executeAndReturnError: &errorDict];
    
    if (returnDescriptor != nil)
    {
        NSString* returnedValue = [returnDescriptor stringValue];        
        NSArray* selectedFiles = [returnedValue componentsSeparatedByString:@"\n"];
        
        NSMutableArray* cleanedUpList = [[NSMutableArray alloc] initWithCapacity:[selectedFiles count]];
        for (NSString* curr in selectedFiles)
        {
            if ([curr length] > 0)
            {
                [cleanedUpList addObject:curr];
            }
        }
        
        NSLog(@"[fileListBuilder] %i selected files\n", [cleanedUpList count] );
        for (NSString* curr in cleanedUpList)
        {
            NSLog(@"  - %@\n", curr);
        }
        
        return cleanedUpList;
    }
    else
    {
        printf("Applescript Execution failed!\n");
        NSLog([returnDescriptor stringValue]);
        NSLog([errorDict description]);
        return nil;
    }
}
