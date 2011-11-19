
#import <Cocoa/Cocoa.h>
#import <stdlib.h>
#import "sendmsg.h"

#define RABBIT ""
//"/opt/rabbit/bin/rabbitvcs_osx "

void sendCommand(NSArray* selectedFiles, int commandid)
{    
    bool acceptsFiles = YES;
    
    NSMutableArray* arguments = [[NSMutableArray alloc] initWithCapacity:32];

    
    switch (commandid)
    {
        case ADD:
            [arguments addObject:@"add"];
            break;
            
        case ANNOTATE:
            [arguments addObject:@"annotate"];
            break;
            
        case CHECK_FOR_MODS:
            [arguments addObject:@"checkmods"];
            break;
            
        case CHECKOUT:
            [arguments addObject:@"checkout"];
            break;
            
        case CLEANUP:
            [arguments addObject:@"cleanup"];
            break;
            
        case COMMIT:
            [arguments addObject:@"commit"];
            break;
            
        case DELETE:
            [arguments addObject:@"delete"];
            break;
            
        case EXPORT:
            [arguments addObject:@"export"];
            break;
            
        case DIFF_RAW:
            [arguments addObject:@"diff"];
            break;
            
        case DIFF_GUI:
            [arguments addObject:@"diff"];
            [arguments addObject:@"-s"];
            break;
            
        case IGNORE:
            [arguments addObject:@"ignore"];
            break;
            
        case LOG:
            [arguments addObject:@"log"];
            break;
            
        case MARK_RESOLVED:
            [arguments addObject:@"markresolved"];
            break;
            
        case PROPERTIES:
            [arguments addObject:@"properties"];
            break;
            
        case REVERT:
            [arguments addObject:@"revert"];
            break;
            
        case RENAME:
            [arguments addObject:@"rename"];
            break;
            
        case UPDATE:
            [arguments addObject:@"update"];
            break;
            
        case UPDATE_TO:
            [arguments addObject:@"updateto"];
            break;
            
        case BRANCH:
            [arguments addObject:@"branch"];
            break;
            
        case MERGE:
            [arguments addObject:@"merge"];
            break;
            
        case RELOCATE:
            [arguments addObject:@"relocate"];
            break;
            
        case REPO_BROWSER:
            [arguments addObject:@"browser"];
            break;
            
        case SWITCH:
            [arguments addObject:@"switch"];
            break;
            
        case LOCK:
            [arguments addObject:@"lock"];
            break;
            
        case UNLOCK:
            [arguments addObject:@"unlock"];
            break;
            
        case CREATE_PATCH:
            [arguments addObject:@"createpatch"];
            break;
            
        case APPLY_PATCH:
            [arguments addObject:@"applypatch"];
            break;
            
        case SETTINGS:
            [arguments addObject:@"settings"];
            acceptsFiles = NO;
            break;
            
        case ABOUT:
            [arguments addObject:@"about"];
            acceptsFiles = NO;
            break; 
            
        default:
            fprintf(stderr, "Unknown command %i\n", commandid);
            return;
    }
        

    NSTask* task = [[NSTask alloc] init];
    [task setLaunchPath: @"/opt/rabbit/bin/rabbitvcs_osx"];

    if (acceptsFiles)
    {
        NSLog(@"%i selected files\n", [selectedFiles count] );
        for (NSString* curr in selectedFiles)
        {
            NSLog(@"  - %@\n", curr);
        }
        
        [arguments addObjectsFromArray: selectedFiles];
    }
                 
    [task setArguments:arguments];
    [task launch];
}
