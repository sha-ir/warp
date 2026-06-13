import json, math, os

inp=json.load(open('/home/mhb/warp/.understand-anything/tmp/ua-file-analyzer-input-4.json'))
imp=inp['batchImportData']
ext=json.load(open('/home/mhb/warp/.understand-anything/tmp/ua-file-extract-results-4.json'))
res={r['path']:r for r in ext['results']}

nodes=[]
edges=[]
seen_ids=set()

def add_node(n):
    if n['id'] in seen_ids:
        raise SystemExit('DUP NODE '+n['id'])
    seen_ids.add(n['id'])
    nodes.append(n)

def E(s,t,ty,w):
    if s==t: return
    edges.append({'source':s,'target':t,'type':ty,'direction':'forward','weight':w})

def fnode(path,name,summary,tags,complexity):
    r=res[path]
    lr=None
    for f in r['functions']:
        if f['name']==name:
            lr=[f['startLine'],f['endLine']]; break
    nid='function:%s:%s'%(path,name)
    n={'id':nid,'type':'function','name':name,'filePath':path,'summary':summary,'tags':tags,'complexity':complexity}
    if lr: n['lineRange']=lr
    add_node(n)
    E('file:'+path,nid,'contains',1.0)
    exn=set(e['name'] for e in r['exports'])
    if name in exn:
        E('file:'+path,nid,'exports',0.8)
    return nid

def cnode(path,name,summary,tags,complexity,kind='class'):
    r=res[path]
    lr=None
    for c in r['classes']:
        if c['name']==name:
            lr=[c['startLine'],c['endLine']]; break
    nid='class:%s:%s'%(path,name)
    n={'id':nid,'type':'class','name':name,'filePath':path,'summary':summary,'tags':tags,'complexity':complexity}
    if lr: n['lineRange']=lr
    add_node(n)
    E('file:'+path,nid,'contains',1.0)
    exn=set(e['name'] for e in r['exports'])
    if name in exn:
        E('file:'+path,nid,'exports',0.8)
    return nid

def filenode(path,summary,tags,complexity,notes=None):
    name=path.split('/')[-1]
    n={'id':'file:'+path,'type':'file','name':name,'filePath':path,'summary':summary,'tags':tags,'complexity':complexity}
    if notes: n['languageNotes']=notes
    add_node(n)

# ---------- FILE NODES + members ----------
P='crates/warpui_core/src/'

# accessibility.rs
f=P+'accessibility.rs'
filenode(f,"Defines the accessibility model for UI elements: content/help text, verbosity levels, and the WarpA11yRole taxonomy mapped to platform a11y roles.",["accessibility","data-model","type-definition","a11y"],"moderate")
cnode(f,'AccessibilityContent',"Builder-style struct holding an element's accessible value, optional help text, frame and role, with constructors for varying verbosity.",["accessibility","data-model","builder"],"moderate")
cnode(f,'WarpA11yRole',"Enum taxonomy of accessibility roles (Button, Checkbox, Image, Link, Menu, etc.) with Display formatting to platform role strings.",["accessibility","enum","type-definition"],"simple")
cnode(f,'ActionAccessibilityContent',"Enum describing how an action contributes accessibility content: empty, custom static, or computed via closure.",["accessibility","enum","type-definition"],"simple")
cnode(f,'AccessibilityVerbosity',"Verbosity setting (Verbose/Concise) controlling how much accessibility detail is announced.",["accessibility","enum","type-definition"],"simple")
fnode(f,'string_announcement',"Composes the spoken announcement string for an element from its value, role, and help text honoring verbosity.",["accessibility","formatting","a11y"],"moderate")

# actions.rs
f=P+'actions.rs'
filenode(f,"Declares StandardAction, the enum of OS-level window/application actions (Close, Hide, Quit, Zoom, Minimize, etc.) recognized by the framework.",["type-definition","actions","enum"],"simple")
cnode(f,'StandardAction',"Enum of standard platform window/application actions such as Close, Hide, Quit, Zoom, and Minimize.",["actions","enum","type-definition"],"simple")

# app_focus_telemetry.rs
f=P+'app_focus_telemetry.rs'
filenode(f,"Tracks application focus/blur timing and accumulates daily app-focus duration for telemetry, syncing once per day.",["telemetry","service","data-model"],"moderate")
cnode(f,'AppFocusInfo',"Holds last-focus timestamp and daily accumulated focus duration; records focus/blur transitions for telemetry.",["telemetry","data-model","service"],"moderate")
cnode(f,'DailyAppFocusDuration',"Accumulator for a single day's focused duration, resetting and re-syncing when the day rolls over.",["telemetry","data-model"],"simple")
fnode(f,'try_record',"Records elapsed focus duration into the daily accumulator, resetting it when crossing into a new day.",["telemetry","accumulator"],"simple")
fnode(f,'record_app_focus',"Marks the moment the app gained focus by stamping the current time.",["telemetry","event-handler"],"simple")
fnode(f,'record_app_blur',"On blur, computes elapsed focused time and folds it into the daily focus accumulator.",["telemetry","event-handler"],"simple")

# app_focus_telemetry_tests.rs
f=P+'app_focus_telemetry_tests.rs'
filenode(f,"Unit test verifying that daily app-focus duration accumulates correctly across focus/blur cycles.",["test","telemetry"],"simple")

# assets/asset_cache.rs
f=P+'assets/asset_cache.rs'
filenode(f,"Asynchronous asset cache: loads, stores, and evicts raw asset bytes (images/fonts) from bundled, local-file, async, or raw sources with size-based eviction.",["service","asset-cache","async","caching"],"complex","Uses async executors (foreground/background) and trait objects (AssetSource, AssetProvider) for pluggable asset loading.")
cnode(f,'AssetCache',"Central async cache that loads assets from multiple sources, tracks raw byte size, evicts when over budget, and shares loading futures.",["service","caching","async","asset-cache"],"complex")
cnode(f,'AssetSource',"Enum of where an asset comes from: Async fetch, Bundled, LocalFile, or Raw in-memory bytes.",["enum","type-definition","asset-cache"],"simple")
cnode(f,'AssetState',"Public enum describing an asset's lifecycle state: Loading, Loaded, Evicted, or FailedToLoad.",["enum","type-definition","asset-cache"],"simple")
cnode(f,'AssetHandle',"Handle to a requested asset (source + type) that can await its loaded state.",["data-model","asset-cache"],"simple")
cnode(f,'AsyncAssetId',"Namespaced identifier for an asynchronously fetched asset.",["data-model","asset-cache","type-definition"],"simple")
fnode(f,'load_asset',"Resolves an asset handle, returning cached bytes or initiating asynchronous loading from its source.",["asset-cache","async","caching"],"complex")
fnode(f,'load_asynchronously',"Drives the async loading pipeline for an asset: fetches bytes, decodes, stores, and notifies waiters.",["asset-cache","async"],"complex")
fnode(f,'evict_raw_assets_if_needed',"Evicts least-needed raw assets when total cached byte size exceeds the configured budget.",["asset-cache","caching","eviction"],"moderate")
fnode(f,'insert_raw_asset_bytes',"Inserts decoded raw asset bytes into the cache, updating size accounting and state.",["asset-cache","caching"],"moderate")

# assets/mod.rs
f=P+'assets/mod.rs'
filenode(f,"Assets module barrel: re-exports the asset cache and declares the AssetProvider trait for bundled asset lookup.",["barrel","entry-point","asset-cache"],"simple")
cnode(f,'AssetProvider',"Trait for resolving bundled assets by key.",["trait","type-definition","asset-cache"],"simple")

# clipboard.rs
f=P+'clipboard.rs'
filenode(f,"Clipboard abstraction: the Clipboard trait plus ClipboardContent/ImageData value types and an in-memory test implementation.",["clipboard","type-definition","data-model"],"moderate")
cnode(f,'Clipboard',"Trait abstracting read/write of clipboard content including primary-selection variants.",["clipboard","trait","type-definition"],"moderate")
cnode(f,'ClipboardContent',"Value type carrying plain text, file paths, HTML, and image payloads for a clipboard transfer.",["clipboard","data-model"],"moderate")
cnode(f,'InMemoryClipboard',"In-memory Clipboard implementation used for testing.",["clipboard","test","mock"],"simple")
fnode(f,'should_insert_text_on_paste',"Decides whether plain text should be inserted on paste based on content shape (text vs image/files).",["clipboard","validation"],"simple")

# clipboard_utils.rs
f=P+'clipboard_utils.rs'
filenode(f,"Clipboard helper functions: extract filenames from text/HTML, sanitize HTML to plain text, and convert/normalize clipboard image data.",["clipboard","utility","serialization"],"complex")
fnode(f,'strip_html_to_plain_text',"Strips HTML markup down to plain text, handling tags, entities, and whitespace normalization.",["clipboard","serialization","parsing"],"complex")
fnode(f,'extract_filename_from_html',"Parses pasted HTML to recover an originating filename from tag attributes.",["clipboard","parsing"],"moderate")
fnode(f,'extract_filename_from_text',"Heuristically extracts a filename from pasted plain text.",["clipboard","parsing"],"moderate")
fnode(f,'convert_raw_bitmap_to_png',"Encodes a raw bitmap clipboard image into PNG bytes.",["clipboard","serialization","image"],"moderate")
fnode(f,'read_images_from_clipboard',"Reads and normalizes image payloads from clipboard content into usable image data.",["clipboard","image"],"moderate")
fnode(f,'extract_filename_from_clipboard_content',"Picks the best available filename for clipboard content across text and HTML sources.",["clipboard","parsing"],"simple")

# clipboard_utils_tests.rs
f=P+'clipboard_utils_tests.rs'
filenode(f,"Unit tests for clipboard filename extraction and image-content handling helpers.",["test","clipboard"],"moderate")

# core/action.rs
f=P+'core/action.rs'
filenode(f,"Core action plumbing: the dynamic Action trait (downcastable, type-named) and ActionType identity helper.",["type-definition","actions","core"],"simple")
cnode(f,'Action',"Trait for dynamically-typed actions supporting downcast via as_any and a stable type name.",["actions","trait","type-definition","core"],"simple")

# core/app.rs
f=P+'core/app.rs'
filenode(f,"Heart of the framework: AppContext owns models, views, windows, ref-counts, executors, and the dispatch/subscription machinery; App is the public facade over it.",["core","entry-point","app-context","service"],"complex","Massive central context type; uses interior mutability, foreground/background executors, and an effect-flush event loop driving view/model notifications.")
cnode(f,'AppContext',"The central mutable application context holding models, singleton models, windows, ref-counts, executors, and platform delegate; coordinates dispatch, subscriptions, spawning, and window lifecycle.",["core","app-context","service","singleton"],"complex")
cnode(f,'App',"Public facade wrapping AppContext, exposing window bounds, focus, presenter, executors, and high-level dispatch entry points.",["core","facade","entry-point","app-context"],"complex")
fnode(f,'new',"Constructs an AppContext with platform delegate, executors, font sources, and empty model/view/window registries.",["core","app-context","constructor"],"moderate")
fnode(f,'with_foreground_executor',"Runs a closure with the foreground executor bound, draining pending effects and flushing notifications afterward.",["core","app-context","scheduling"],"complex")
fnode(f,'dispatch_action',"Routes a dynamically-typed action to the focused view's handler chain, bubbling up ancestors until handled.",["core","actions","dispatch","event-handler"],"complex")
fnode(f,'add_typed_action',"Registers a strongly-typed action handler with keymap binding and accessibility metadata.",["core","actions","registration"],"complex")
fnode(f,'add_action',"Registers a dynamic action handler keyed by action type for later dispatch.",["core","actions","registration"],"moderate")
fnode(f,'register_global_shortcut',"Registers an OS-level global shortcut mapping a keystroke to an action with the platform.",["core","keybinding","platform"],"moderate")
fnode(f,'subscribe_to_view',"Subscribes an observer to a view's notifications, returning a Subscription that auto-unsubscribes on drop.",["core","subscription","event-handler"],"moderate")
fnode(f,'add_window_with_bounds',"Creates a new platform window at the given bounds/style and registers its root view.",["core","window","platform"],"moderate")
fnode(f,'show_native_platform_modal',"Presents a native OS modal dialog and wires its response back through the app's effect loop.",["core","platform","modal"],"moderate")

# core/autotracking/mod.rs
f=P+'core/autotracking/mod.rs'
filenode(f,"Automatic dependency tracking for rendering: records which views/values a render reads so re-renders can be invalidated precisely.",["core","reactivity","autotracking","invalidation"],"moderate")
fnode(f,'render_view',"Renders a view while recording its read dependencies into the tracking cache for later invalidation.",["core","reactivity","autotracking"],"moderate")
fnode(f,'track_read',"Records a read of a tracked value/view against the currently-rendering view's dependency set.",["core","reactivity","autotracking"],"moderate")
fnode(f,'close_window',"Clears tracking state associated with a window when it is closed.",["core","autotracking","cleanup"],"simple")

# core/autotracking/tracked.rs
f=P+'core/autotracking/tracked.rs'
filenode(f,"Defines Tracked<T>, a wrapper whose reads are recorded by the autotracking system, plus a monotonic TrackedId allocator.",["core","reactivity","autotracking","type-definition"],"simple")
cnode(f,'Tracked',"Wrapper around a value that registers a dependency every time it is read under autotracking.",["reactivity","autotracking","data-model"],"simple")

# core/entity.rs
f=P+'core/entity.rs'
filenode(f,"Core entity identity: EntityId plus the Entity/SingletonEntity marker traits and singleton-model accessor traits.",["core","type-definition","entity","trait"],"simple")
cnode(f,'EntityId',"Opaque unique identifier for a model or view entity.",["core","entity","type-definition"],"simple")

# core/mod.rs
f=P+'core/mod.rs'
filenode(f,"Core module root: declares the framework's foundational types — AnyView, Effect, Handle, RefCounts, Subscription/Observation, retry strategy, and window/display ids — and wires submodules.",["core","barrel","type-definition","reactivity"],"complex","Central type hub for the bespoke retained-mode UI runtime; defines the effect/subscription model and ref-counting for entities.")
cnode(f,'AnyView',"Type-erased view trait exposing rendering, focus/blur, keymap context, cursor position, and accessibility hooks.",["core","trait","view","type-definition"],"moderate")
cnode(f,'Effect',"Enum of deferred effects (events, model/view notifications, focus changes, typed/global actions) processed by the app's flush loop.",["core","enum","reactivity","event-handler"],"moderate")
cnode(f,'RefCounts',"Tracks entity reference counts and collects dropped models/views for cleanup.",["core","memory","reactivity"],"moderate")
cnode(f,'RetryOption',"Configurable retry policy (linear/exponential backoff with jitter) used by spawn-with-retry helpers.",["core","retry","scheduling"],"moderate")
cnode(f,'Subscription',"Enum representing an active subscription from a model, view, or app, carrying its unsubscribe key.",["core","subscription","reactivity"],"simple")
cnode(f,'Handle',"Trait for entity handles exposing id and source-location identity.",["core","trait","type-definition"],"simple")

# core/mod_tests.rs
f=P+'core/mod_tests.rs'
filenode(f,"Extensive integration-style tests for the core runtime: view nesting, focus/blur, subscriptions, notifications, and effect dispatch using a NestedView harness.",["test","core","reactivity"],"complex")

# core/model/context.rs
f=P+'core/model/context.rs'
filenode(f,"ModelContext: the per-model handle into the app, providing subscribe/observe/notify and a family of spawn (local/abortable/stream/retry) task helpers.",["core","model","context","async"],"complex")
cnode(f,'ModelContext',"Context passed to model update closures, exposing the owning app plus subscription, observation, notification, and task-spawning APIs scoped to the model.",["core","model","context","service"],"complex")
fnode(f,'spawn_local',"Spawns a model-scoped local future whose result is delivered back into the model on the foreground executor.",["core","async","model","scheduling"],"moderate")
fnode(f,'spawn_abortable',"Spawns an abortable model-scoped task, returning a handle that cancels the future when dropped.",["core","async","model","scheduling"],"complex")
fnode(f,'spawn_with_retry_on_error_when',"Spawns a model task that retries on error according to a RetryOption while a predicate holds.",["core","async","model","retry"],"complex")
fnode(f,'subscribe_to_model',"Subscribes this model to another model's notifications, returning an auto-cleaning Subscription.",["core","model","subscription"],"moderate")
fnode(f,'unsubscribe_from_model',"Tears down a model subscription, removing observer bookkeeping from the app.",["core","model","subscription"],"moderate")
fnode(f,'notify',"Queues a notification effect so observers of this model are informed on the next flush.",["core","model","reactivity"],"moderate")

# core/model/handle.rs
f=P+'core/model/handle.rs'
filenode(f,"Model handles: strong ModelHandle<T>, type-erased AnyModelHandle, and WeakModelHandle, plus Read/UpdateModel access traits with ref-count integration.",["core","model","handle","type-definition"],"moderate")
cnode(f,'ModelHandle',"Strongly-typed reference-counted handle to a model entity.",["core","model","handle"],"simple")
cnode(f,'AnyModelHandle',"Type-erased model handle supporting downcast and reference-count lifecycle management.",["core","model","handle"],"moderate")
cnode(f,'WeakModelHandle',"Non-owning weak reference to a model that can be upgraded if still alive.",["core","model","handle"],"simple")

# core/model/mod.rs
f=P+'core/model/mod.rs'
filenode(f,"Model submodule barrel: re-exports ModelContext and the handle types and declares the AnyModel trait.",["barrel","core","model","entry-point"],"simple")

# core/ref_count_tests.rs
f=P+'core/ref_count_tests.rs'
filenode(f,"Tests verifying entity reference counting: models and views are dropped exactly when their last handle is released.",["test","core","memory"],"moderate")

# core/transfer_view_tests.rs
f=P+'core/transfer_view_tests.rs'
filenode(f,"Tests for transferring views between windows, validating subscription/observation migration and lifecycle correctness.",["test","core","view","window"],"complex")

# core/view/context.rs
f=P+'core/view/context.rs'
filenode(f,"ViewContext: the per-view handle into the app exposing element positions, subscriptions, file pickers, notifications, native modals, and view-scoped task spawning.",["core","view","context","async"],"complex")
cnode(f,'ViewContext',"Context passed to view render/update closures, providing access to the app, window/view ids, subscriptions, platform dialogs, and task spawning scoped to the view.",["core","view","context","service"],"complex")
fnode(f,'spawn_abortable',"Spawns an abortable view-scoped task whose future is cancelled when its handle drops.",["core","async","view","scheduling"],"complex")
fnode(f,'unsubscribe_to_view',"Removes a view-to-view subscription and its observer bookkeeping from the app.",["core","view","subscription"],"moderate")
fnode(f,'unsubscribe_to_model',"Removes a view-to-model subscription and associated observer state.",["core","view","subscription"],"moderate")
fnode(f,'open_file_picker',"Opens the native open-file dialog scoped to this view and delivers the selection asynchronously.",["core","view","platform","file-picker"],"moderate")
fnode(f,'show_native_platform_modal',"Shows a native modal from view context and routes the response back to the view.",["core","view","platform","modal"],"moderate")
fnode(f,'subscribe_to_view',"Subscribes this view to another view's notifications with an auto-unsubscribing handle.",["core","view","subscription"],"moderate")

# core/view/handle.rs
f=P+'core/view/handle.rs'
filenode(f,"View handles: strong ViewHandle<T>, type-erased AnyViewHandle, and upgradable WeakViewHandle, with Read/UpdateView access traits.",["core","view","handle","type-definition"],"moderate")
cnode(f,'ViewHandle',"Strongly-typed reference-counted handle to a view within a window.",["core","view","handle"],"simple")
cnode(f,'AnyViewHandle',"Type-erased view handle supporting downcast and ref-count lifecycle management.",["core","view","handle"],"moderate")
cnode(f,'WeakViewHandle',"Non-owning weak reference to a view that can be upgraded when still alive.",["core","view","handle"],"simple")

# core/view/mod.rs
f=P+'core/view/mod.rs'
filenode(f,"View submodule root: defines the View and TypedActionView traits, focus/blur context enums, and accessibility data, re-exporting view context and handles.",["core","view","trait","type-definition"],"moderate")
cnode(f,'View',"Core trait every view implements: render, focus/blur hooks, keymap context, cursor position, and accessibility contents.",["core","view","trait","type-definition"],"moderate")
cnode(f,'TypedActionView',"Trait extending a view to handle a specific typed action and contribute its accessibility content.",["core","view","actions","trait"],"simple")

# core/window.rs
f=P+'core/window.rs'
filenode(f,"Window type: a WindowId plus the Window struct tracking its views, root view, and focused view.",["core","window","data-model"],"simple")
cnode(f,'Window',"Holds a window's view registry, root view, and currently focused view.",["core","window","data-model"],"simple")

# elements/event_handler.rs
f=P+'elements/event_handler.rs'
filenode(f,"EventHandler element: wraps a child element with mouse/keyboard/modifier callbacks and dispatches input events to the appropriate handler.",["component","event-handler","input"],"complex")
cnode(f,'EventHandler',"Builder element that attaches keydown, modifier, and per-button mouse callbacks around a child element.",["component","event-handler","builder","input"],"complex")
cnode(f,'MouseInBehavior',"Configures when mouse-in callbacks fire (on synthetic events, when covered).",["event-handler","type-definition","input"],"simple")
fnode(f,'dispatch_event',"Routes an incoming input event (mouse buttons, movement, keydown, modifier changes) to the matching registered callback.",["event-handler","input","dispatch"],"complex")
fnode(f,'new',"Constructs an EventHandler wrapping the given child element with no callbacks bound.",["component","event-handler","constructor"],"moderate")

# elements/icon.rs
f=P+'elements/icon.rs'
filenode(f,"Icon element: an asset-backed, optionally tinted/scaled icon that lays out and paints itself within the rendering pipeline.",["component","rendering","ui-element"],"moderate")
cnode(f,'Icon',"Renderable icon element loading from an asset path with configurable opacity, color tint, and size.",["component","rendering","ui-element"],"moderate")
fnode(f,'paint',"Paints the loaded icon asset at its laid-out bounds applying color tint and opacity.",["rendering","ui-element"],"moderate")

# elements/image.rs
f=P+'elements/image.rs'
filenode(f,"Image element: renders static and animated images from assets with fit modes, corner radius, opacity, and graceful loading/backup states.",["component","rendering","ui-element","image"],"complex")
cnode(f,'Image',"Renderable image element supporting fit modes (cover/contain/stretch), corner radius, opacity, animation, and backup elements during load.",["component","rendering","ui-element","image"],"complex")
fnode(f,'paint',"Paints the image — static or animated — applying fit, corner radius, and opacity, or a backup element while loading.",["rendering","ui-element","image"],"complex")
fnode(f,'paint_static_image',"Paints a single-frame image into its computed rectangle with the configured fit and styling.",["rendering","ui-element","image"],"moderate")
fnode(f,'paint_animated_image',"Advances and paints the current frame of an animated image based on elapsed time.",["rendering","ui-element","image","animation"],"moderate")
fnode(f,'layout',"Computes the image element's layout size and paint bounds from source dimensions and fit mode.",["rendering","layout","ui-element"],"moderate")

# fonts/external_fallback.rs
f=P+'fonts/external_fallback.rs'
filenode(f,"External font fallback: requests and loads remote fallback font families (for glyphs/lines/text frames) via the asset cache, emitting load events.",["fonts","async","asset-cache","service"],"moderate")
cnode(f,'FallbackFontModel',"Model that requests external fallback fonts and notifies when a fallback family finishes loading.",["fonts","service","async"],"moderate")
cnode(f,'ExternalFontFamily',"Describes an external fallback font family by name and the URLs of its font files.",["fonts","data-model","type-definition"],"simple")
fnode(f,'request_fallback_font_for_char',"Requests an external fallback font capable of rendering a specific character.",["fonts","async","fallback"],"moderate")
fnode(f,'app_font_fallback',"Resolves the application-level fallback font source for missing glyphs.",["fonts","fallback"],"moderate")

# ---------- IMPORT EDGES (1:1) ----------
imp_count=0
for path, targets in imp.items():
    for t in targets:
        E('file:'+path,'file:'+t,'imports',0.7)
        imp_count+=1

# ---------- tested_by EDGES ----------
E('file:'+P+'app_focus_telemetry.rs','file:'+P+'app_focus_telemetry_tests.rs','tested_by',0.5)
E('file:'+P+'clipboard_utils.rs','file:'+P+'clipboard_utils_tests.rs','tested_by',0.5)
E('file:'+P+'clipboard.rs','file:'+P+'clipboard_utils_tests.rs','tested_by',0.5)
E('file:'+P+'core/mod.rs','file:'+P+'core/mod_tests.rs','tested_by',0.5)
E('file:'+P+'core/mod.rs','file:'+P+'core/ref_count_tests.rs','tested_by',0.5)
E('file:'+P+'core/mod.rs','file:'+P+'core/transfer_view_tests.rs','tested_by',0.5)

# ---------- a few high-confidence calls/depends ----------
# clipboard_utils builds on clipboard types
E('file:'+P+'clipboard_utils.rs','file:'+P+'clipboard.rs','depends_on',0.6)
# icon/image depend on asset cache
E('file:'+P+'elements/icon.rs','class:'+P+'assets/asset_cache.rs:AssetCache','depends_on',0.6)
E('file:'+P+'elements/image.rs','class:'+P+'assets/asset_cache.rs:AssetCache','depends_on',0.6)
E('file:'+P+'fonts/external_fallback.rs','class:'+P+'assets/asset_cache.rs:AssetCache','depends_on',0.6)

print('NODES',len(nodes),'EDGES',len(edges),'IMPORTS',imp_count)

# ---------- SPLIT ----------
batchIndex=4
N=len(nodes); Ec=len(edges)
parts=max(1, math.ceil(max(N/60.0, Ec/120.0)))
outdir='/home/mhb/warp/.understand-anything/intermediate'
os.makedirs(outdir,exist_ok=True)

files_sorted=sorted(imp.keys())  # all 29 paths
# group files into parts
chunk=math.ceil(len(files_sorted)/parts)
groups=[set(files_sorted[i:i+chunk]) for i in range(0,len(files_sorted),chunk)]
# ensure exactly len(groups) parts
def node_file(n):
    return n.get('filePath')
written=[]
nid_to_part={}
part_nodes=[[] for _ in groups]
for n in nodes:
    fp=node_file(n)
    pi=None
    for i,g in enumerate(groups):
        if fp in g: pi=i;break
    if pi is None: pi=0
    part_nodes[pi].append(n)
    nid_to_part[n['id']]=pi
# edges grouped by source node's part; source is always a node we created (file/class)
src_part={}
for n in nodes: src_part[n['id']]=nid_to_part[n['id']]
part_edges=[[] for _ in groups]
for e in edges:
    s=e['source']
    pi=src_part.get(s)
    if pi is None:
        # source is a file: node; map by path
        if s.startswith('file:'):
            fp=s[5:]
            for i,g in enumerate(groups):
                if fp in g: pi=i;break
    if pi is None: pi=0
    part_edges[pi].append(e)

total_n=total_e=0
for i in range(len(groups)):
    frag={'nodes':part_nodes[i],'edges':part_edges[i]}
    if len(groups)==1:
        fn=outdir+'/batch-%d.json'%batchIndex
    else:
        fn=outdir+'/batch-%d-part-%d.json'%(batchIndex,i+1)
    json.dump(frag,open(fn,'w'),indent=1)
    written.append((fn,len(part_nodes[i]),len(part_edges[i])))
    total_n+=len(part_nodes[i]); total_e+=len(part_edges[i])

print('PARTS',len(groups))
for w in written: print(w)
print('TOTAL nodes',total_n,'edges',total_e)
