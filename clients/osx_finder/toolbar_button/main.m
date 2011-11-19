
#import <Cocoa/Cocoa.h>
#import "fileListBuilder.h"
#import "sendmsg.h"


// -------------------------------------------------------------------
//
// MyMenu
// 
// Creates and manages the menu display.
//
// Interface
// -------------------------------------------------------------------
@interface MyMenu : NSObject
{
    NSMenu* menu;
    
    NSMutableArray* menuItems;
    NSArray* selectedFiles;

    BOOL containsFolders;
    BOOL containsFiles;
    
    int selection;
}
-(id) init;

-(NSMutableArray*)menuItems;
-(void)setMenuItems:(NSMutableArray*)newMenuItems;

-(NSArray*)selectedFiles;
-(void)setSelectedFiles:(NSArray *)newSelectedFiles;

- (void) fillMenu;
-(void) addItem:(NSString*) name withIcon:(NSImage*) image andId:(enum MenuItems)menutag;

-(void)dealloc;

-(void)menu:(NSMenu *)shownMenu willHighlightItem:(NSMenuItem *)item;
-(void)menuDidClose:(NSMenu *)menu;

@end


NSImage* imageAdd;
NSImage* imageAnnotate;
NSImage* imageBranch;
NSImage* imageCheckmods;
NSImage* imageCheckout;
NSImage* imageCleanup;
NSImage* imageCommit;
NSImage* imageDelete;
NSImage* imageDiff;
NSImage* imageExport;
NSImage* imageIgnore;
NSImage* imageLock;
NSImage* imageLog;
NSImage* imageMerge;
NSImage* imagePatchCreate;
NSImage* imagePatchApply;
NSImage* imageProperties;
NSImage* imageRelocate;
NSImage* imageRepobrowser;
NSImage* imageRename;
NSImage* imageResolve;
NSImage* imageRevert;
NSImage* imageSettings;
NSImage* imageSwitch;
NSImage* imageUnlock;
NSImage* imageUpdate;

// -------------------------------------------------------------------
//
// MyMenu
// 
// Creates and manages the menu display.
//
// Implementation
// -------------------------------------------------------------------
@implementation MyMenu

// -------------------------------------------------------------------
// 
// menu:willHighlightItem:
//
// Returns index of requested menu item (or -1, if not in menu)
//
// -------------------------------------------------------------------
- (void)menu:(NSMenu *)shownMenu willHighlightItem:(NSMenuItem *)item
{
    selection = -1;
    int amount = [menuItems count];
    for(int i=0; i<amount; i++)
    {
        NSMenuItem* item_i = [menuItems objectAtIndex:i];
        if(item_i == item)
        {
            selection = i;
            break;
        }
    }
    
}

// -------------------------------------------------------------------
// 
// menuDidClose:
//
// Window (menu) Delegate method.
// Computes command index number used by Daemon
// Sends command to Daemon
//
// -------------------------------------------------------------------
- (void)menuDidClose:(NSMenu *)shownMenu
{
    if (selection == -1) return;
    
    //int numberOfItems = [shownMenu numberOfItems];
    int tag = [[menuItems objectAtIndex:selection] tag];
    
#ifdef DEBUG
    NSLog(@"Selected item %i", tag);
#endif
    
    if (tag < 1) return;
    
    sendCommand(selectedFiles, tag);

    
    /*
    if (selection == [shownMenu numberOfItems] - 2) {
        // Last two items are
        //   separator, which doesn't count in selection count
        //   About, which is therefore (numberOfItems - 2)
        //    -1 for the zero-based item index
        //    -another for the un-selection-counted separator
        //
        // Convention, over in -[SCUIDaemonController+PluginSupport handleSelection:] is "About is -2"
        sendCommand(selectedFiles, -2);
    }
    else if (selection >= 0) {
        // Ordinary commands invoked by selection number
        sendCommand(selectedFiles, selection);
    }
    // else, clicked outside menu, hit escape, or like that
    */
    
    //[[NSApplication sharedApplication] terminate: nil]; // Never returns
}

-(void) addItem:(NSString*) name withIcon:(NSImage*) image andId:(enum MenuItems)menutag
{
    NSMenuItem* item = [menu addItemWithTitle:NSLocalizedStringFromTable(name, @"menuitems", nil) action:nil keyEquivalent:@""];
    [item setEnabled:YES];
    [item setImage:image];
    [item setTag:menutag];
    [menuItems addObject:item];
}

// -------------------------------------------------------------------
// 
// fillMenu
//
// Populates the menu with known Subversion commands
//
// -------------------------------------------------------------------
- (void) fillMenu
{
    NSString* title = [[NSString alloc] initWithCString:"My Menu" encoding:NSUTF8StringEncoding];
    menu = [[NSMenu alloc] initWithTitle:title];
    
    [self addItem:@"Add" withIcon:imageAdd andId:ADD];
    
    if (containsFiles && !containsFolders)
    {
        [self addItem:@"Annotate" withIcon:imageAnnotate andId:ANNOTATE];
    }
    
    [self addItem:@"Check for modifications" withIcon:imageCheckmods andId:CHECK_FOR_MODS];
    
    if (containsFolders && !containsFiles)
    {
        [self addItem:@"Checkout" withIcon:imageCheckout andId:CHECKOUT];
        [self addItem:@"Cleanup" withIcon:imageCleanup andId:CLEANUP];
    }
    [self addItem:@"Commit" withIcon:imageCommit andId:COMMIT];
    [self addItem:@"Delete" withIcon:imageDelete andId:DELETE];
    [self addItem:@"Export" withIcon:imageExport andId:EXPORT];
    [self addItem:@"Diff against base (raw)" withIcon:imageDiff andId:DIFF_RAW];
    [self addItem:@"Diff against base (side by side)" withIcon:imageDiff andId:DIFF_GUI];
    //[self addItem:@"Ignore" withIcon:imageIgnore andId:IGNORE];
    [self addItem:@"Log" withIcon:imageLog andId:LOG];
    [self addItem:@"Mark Resolved" withIcon:imageResolve andId:MARK_RESOLVED];
    [self addItem:@"Properties" withIcon:imageProperties andId:PROPERTIES];
    [self addItem:@"Revert" withIcon:imageRevert andId:REVERT];
    [self addItem:@"Rename" withIcon:imageRename andId:RENAME];
    [self addItem:@"Update" withIcon:imageUpdate andId:UPDATE];
    [self addItem:@"Update to revision..." withIcon:imageUpdate andId:UPDATE_TO];
    
    if (containsFolders && !containsFiles)
    {
        [menu addItem:[NSMenuItem separatorItem]];
        [self addItem:@"Branch/Tag" withIcon:imageBranch andId:BRANCH];
        [self addItem:@"Merge" withIcon:imageMerge andId:MERGE];
        [self addItem:@"Relocate" withIcon:imageRelocate andId:RELOCATE];
        [self addItem:@"Repository Browser" withIcon:imageRepobrowser andId:REPO_BROWSER];
        [self addItem:@"Switch" withIcon:imageSwitch andId:SWITCH];
    }
    
    [menu addItem:[NSMenuItem separatorItem]];
    
    [self addItem:@"Lock" withIcon:imageLock andId:LOCK];
    [self addItem:@"Unlock" withIcon:imageUnlock andId:UNLOCK];
    [menu addItem:[NSMenuItem separatorItem]];

    [self addItem:@"Create Patch" withIcon:imagePatchCreate andId:CREATE_PATCH];
    [self addItem:@"Apply Patch" withIcon:imagePatchApply andId:APPLY_PATCH];
    [menu addItem:[NSMenuItem separatorItem]];

    [self addItem:@"Settings" withIcon:imageSettings andId:SETTINGS];
    [self addItem:@"About" withIcon:nil andId:ABOUT];

    [menu setAutoenablesItems:NO];
    [menu setDelegate:self];
    [menu sizeToFit];
}


// -------------------------------------------------------------------
// 
// init
//
// Initializes and posts the menu
//
// -------------------------------------------------------------------
-(id) init
{
    self = [super init];

    if (self)
    {
        [self setMenuItems:[[NSMutableArray alloc] init]];
    
        containsFolders = NO;
        containsFiles = NO;
        [self setSelectedFiles:getSelectedFilesList(&containsFolders, &containsFiles)];
    
        if ([self selectedFiles] == nil)
        {
            fprintf(stderr, "Getting list of files failed");
            // FIXME : report something to user
            exit(1);
        }
    
        selection = -1;
    
        BOOL pullsDown = NO;
        
        NSPoint mouseLoc = [NSEvent mouseLocation];
#if DEBUG
        NSLog(@"Mouse base location is (%g, %g)", mouseLoc.x, mouseLoc.y);
#endif
        
        NSEnumerator *screenEnum =[[NSScreen screens] objectEnumerator];
        NSScreen *screen;
        while ((screen = [screenEnum nextObject]) && !NSMouseInRect(mouseLoc, [screen frame], NO));
#if DEBUG
        NSLog(@"screen base frame is (%g, %g) + (%g, %g)", 
              [screen frame].origin.x, [screen frame].origin.y,
              [screen frame].size.width, [screen frame].size.height);
#endif
        
        NSPoint menuLoc;
        menuLoc.x = mouseLoc.x - [screen frame].origin.x;
        menuLoc.y = mouseLoc.y - [screen frame].origin.y;
#if DEBUG
        NSLog(@"desired menu screen location is (%g, %g)", menuLoc.x, menuLoc.y);
#endif
        
        //----
        NSWindow *hiddenWindow = [[NSWindow alloc]
                                  initWithContentRect:NSMakeRect( menuLoc.x, menuLoc.y, 5, 5 )
                                  styleMask: NSTitledWindowMask | NSClosableWindowMask 
                                  backing:NSBackingStoreNonretained
                                  defer:NO
                                  screen:screen]; 
        [hiddenWindow setFrameOrigin:mouseLoc]; // dunno why this is needed, but some screen arrangements misposition without
#if DEBUG
        NSLog(@"hidden window base location: %g %g", [hiddenWindow frame].origin.x, [hiddenWindow frame].origin.y);
        NSLog(@"hidden window screen location: %g %g", 
              [hiddenWindow frame].origin.x - [screen frame].origin.x,
              [hiddenWindow frame].origin.y - [screen frame].origin.y
              );
#endif

        //----
        
        NSRect rect;
        rect.origin.x = 0;
        rect.origin.y = 0;
        rect.size.width = 1000;
        rect.size.height = 500;
        
        NSView* view = [[NSView alloc] initWithFrame:rect];
        [[hiddenWindow contentView] addSubview:view];

        [self fillMenu];

        NSRect menuFrame;
        menuFrame.origin.x = 0.0;
        menuFrame.origin.y = 0.0;
        menuFrame.size.width = 100;
        menuFrame.size.height = 0.0;

        NSPopUpButtonCell *popUpButtonCell = [[NSPopUpButtonCell alloc] initTextCell:@"" pullsDown:pullsDown];
        [popUpButtonCell setMenu:menu];
        if (!pullsDown) [popUpButtonCell selectItem:nil];
        
        [popUpButtonCell performClickWithFrame:menuFrame inView:view]; // Never returns
        
    }
    return self;
}

// -------------------------------------------------------------------
// 
// menuItems
//
// Accessor
//
// -------------------------------------------------------------------
-(NSMutableArray*)menuItems
{
    return menuItems;
}

// -------------------------------------------------------------------
// 
// setMenuItems:
//
// Accessor
//
// -------------------------------------------------------------------
-(void)setMenuItems:(NSMutableArray*)newMenuItems
{
    menuItems = newMenuItems;
}

// -------------------------------------------------------------------
// 
// selectedFiles
//
// Accessor
//
// -------------------------------------------------------------------
- (NSArray*) selectedFiles
{
    return selectedFiles;
}

// -------------------------------------------------------------------
// 
// setSelectedFiles:
//
// Accessor
//
// -------------------------------------------------------------------
-(void)setSelectedFiles:(NSArray*)newSelectedFiles
{
    selectedFiles = newSelectedFiles;
}

// -------------------------------------------------------------------
// 
// dealloc
//
// -------------------------------------------------------------------
-(void)dealloc
{
    [self setMenuItems:nil];
    [self setSelectedFiles:nil];
    [super dealloc];
}


@end

// -------------------------------------------------------------------
@interface MyAppDelegate : NSObject
{
}
- (void) applicationDidFinishLaunching:(NSNotification*) notice ;
- (void) applicationDidBecomeActive:(NSNotification *)notif;
@end

// -------------------------------------------------------------------
@implementation MyAppDelegate 
- (void) applicationDidFinishLaunching:(NSNotification*) notice
{
    // DEBUG printf("inside appdidfinishlaunching\n") ;
    [[MyMenu alloc] init]; // Never returns
}
- (void) applicationDidBecomeActive:(NSNotification *)notif
{
    [[MyMenu alloc] init]; // Never returns
}
@end

// -------------------------------------------------------------------
#pragma mark main()

NSImage* loadImage(NSString* name)
{
    NSString * path = [[NSBundle mainBundle] pathForResource:name ofType:@"png"];
    return [[NSImage alloc] initByReferencingFile:path];
}

int main(int argc, char *argv[])
{   
    // TODO : determine which actions are possible
    
    MyAppDelegate* delegate = [[MyAppDelegate alloc] init];
    
    NSApplication* app = [NSApplication sharedApplication];
    
    [app setDelegate:delegate];
    
    imageAdd = loadImage(@"rabbitvcs-add");
    imageAnnotate = loadImage(@"rabbitvcs-annotate");
    imageBranch = loadImage(@"rabbitvcs-branch");
    imageCheckmods = loadImage(@"rabbitvcs-checkmods");
    imageCheckout = loadImage(@"rabbitvcs-checkout");
    imageCleanup = loadImage(@"rabbitvcs-cleanup");
    imageCommit = loadImage(@"rabbitvcs-commit");
    imageDelete = loadImage(@"rabbitvcs-delete");
    imageDiff = loadImage(@"rabbitvcs-diff");
    imageExport = loadImage(@"rabbitvcs-export");
    //imageIgnore = loadImage(@"rabbitvcs-ignore");
    imageLock = loadImage(@"rabbitvcs-lock");
    imageLog = loadImage(@"rabbitvcs-show_log");
    imageMerge = loadImage(@"rabbitvcs-merge");
    imagePatchCreate = loadImage(@"rabbitvcs-createpatch");
    imagePatchApply = loadImage(@"rabbitvcs-applypatch");
    imageProperties = loadImage(@"rabbitvcs-properties");
    imageRelocate = loadImage(@"rabbitvcs-relocate");
    imageRepobrowser = loadImage(@"rabbitvcs-repobrowser");
    imageRename = loadImage(@"rabbitvcs-rename");
    imageResolve = loadImage(@"rabbitvcs-resolve");
    imageRevert = loadImage(@"rabbitvcs-revert");
    imageSettings = loadImage(@"rabbitvcs-settings");
    imageSwitch = loadImage(@"rabbitvcs-switch");
    imageUnlock = loadImage(@"rabbitvcs-unlock");
    imageUpdate = loadImage(@"rabbitvcs-update");
    
    [NSApp run]; // Never returns
    //return NSApplicationMain(argc,  (const char **) argv);
        
    return 0;
}
