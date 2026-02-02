# mGBA Lua Scripting API Reference

Source: https://mgba.io/docs/dev/scripting.html (development version)

## Top-Level Objects

| Object | Description |
|--------|-------------|
| `C` | Table containing exported constants |
| `callbacks` | Singleton CallbackManager for event handling |
| `console` | Singleton for logging (log, warn, error) |
| `util` | Utility functions (expandBitmask, makeBitmask) |
| `emu` | CoreAdapter instance (available when game loads) |
| `socket` | Basic TCP socket library |

---

## CoreAdapter (emu) Methods

### Debugging

```lua
setBreakpoint(callback: function, address: u32, segment: s32 = -1): s64
-- Set a breakpoint at a given address. Returns breakpoint ID.

setWatchpoint(callback: function, address: u32, type: s32, segment: s32 = -1): s64
-- Set a watchpoint at a given address of a given type. Returns watchpoint ID.

setRangeWatchpoint(callback: function, minAddress: u32, maxAddress: u32, type: s32, segment: s32 = -1): s64
-- Set a watchpoint in a given range. Range is exclusive on the end.

clearBreakpoint(cbid: s64): bool
-- Clear a breakpoint or watchpoint by ID returned from set* functions.

currentCycle(): u64
-- Get the current execution cycle.
```

### Memory Access

```lua
read8(address: u32): u32
read16(address: u32): u32
read32(address: u32): u32
readRange(address: u32, length: u32): string
readRegister(regName: string): wrapper

write8(address: u32, value: u8)
write16(address: u32, value: u16)
write32(address: u32, value: u32)
writeRegister(regName: string, value: s32)
```

### Execution Control

```lua
step()          -- Execute single instruction
runFrame()      -- Execute one frame
reset()         -- Reset emulation (invokes reset callback)
```

### State Management

```lua
saveStateFile(path: string, flags: s32 = 31): bool
saveStateSlot(slot: s32, flags: s32 = 31): bool
saveStateBuffer(flags: s32 = 31): string

loadStateFile(path: string, flags: s32 = 29): bool
loadStateSlot(slot: s32, flags: s32 = 29): bool
loadStateBuffer(buffer: string, flags: s32 = 29): bool
```

### ROM/Save Operations

```lua
loadFile(path: string): bool
loadSaveFile(path: string, temporary: bool): bool
autoloadSave(): bool
romSize(): s64
```

### Information

```lua
currentFrame(): u32
getGameTitle(): string
getGameCode(): string
checksum(type: s32 = 0): string
platform(): s32
frequency(): s32
frameCycles(): s32
```

### Input Control

```lua
addKey(key: s32)
addKeys(keys: u32)
clearKey(key: s32)
clearKeys(keys: u32)
setKeys(keys: u32)
getKey(key: s32): s32
getKeys(): u32
```

### Screenshot

```lua
screenshot(filename: string = nil)
screenshotToImage(): Image
```

---

## Constants

### WATCHPOINT_TYPE

```lua
WATCHPOINT_TYPE.WRITE = 1        -- Fires on any write
WATCHPOINT_TYPE.READ = 2         -- Fires on any read
WATCHPOINT_TYPE.RW = 3           -- Fires on read or write
WATCHPOINT_TYPE.WRITE_CHANGE = 5 -- Fires only when value changes (RECOMMENDED)
```

### SAVESTATE Flags

```lua
SAVESTATE.SCREENSHOT = 1
SAVESTATE.SAVEDATA = 2
SAVESTATE.CHEATS = 4
SAVESTATE.RTC = 8
SAVESTATE.METADATA = 16
SAVESTATE.ALL = 31
```

### PLATFORM

```lua
PLATFORM.NONE = -1
PLATFORM.GBA = 0
PLATFORM.GB = 1
```

### GBA_KEY

```lua
GBA_KEY.A = 0
GBA_KEY.B = 1
GBA_KEY.SELECT = 2
GBA_KEY.START = 3
GBA_KEY.RIGHT = 4
GBA_KEY.LEFT = 5
GBA_KEY.UP = 6
GBA_KEY.DOWN = 7
GBA_KEY.R = 8
GBA_KEY.L = 9
```

### INPUT_STATE

```lua
INPUT_STATE.UP = 0
INPUT_STATE.DOWN = 1
INPUT_STATE.HELD = 2
```

### CHECKSUM

```lua
CHECKSUM.CRC32 = 0
```

### SOCKERR

```lua
SOCKERR.OK = 0
SOCKERR.AGAIN = 1
SOCKERR.ADDRESS_IN_USE = 2
SOCKERR.CONNECTION_REFUSED = 3
SOCKERR.DENIED = 4
SOCKERR.FAILED = 5
SOCKERR.NETWORK_UNREACHABLE = 6
SOCKERR.NOT_FOUND = 7
SOCKERR.NO_DATA = 8
SOCKERR.OUT_OF_MEMORY = 9
SOCKERR.TIMEOUT = 10
SOCKERR.UNSUPPORTED = 11
```

---

## Callbacks

Register via `callbacks:add(name, function)`, remove via `callbacks:remove(cbid)`.

| Callback | Description |
|----------|-------------|
| `frame` | Emulation finished a frame |
| `keysRead` | About to read key input |
| `reset` | Emulation reset |
| `start` | Emulation started |
| `stop` | Voluntary shutdown |
| `shutdown` | Powered off |
| `crashed` | Emulation crashed |
| `alarm` | In-game alarm triggered |
| `sleep` | Low-power mode entered |
| `savedataUpdated` | Save data modified |

---

## Socket API

### Creation

```lua
socket.tcp(): Socket              -- Create new socket
socket.connect(addr, port): Socket -- Create connected socket
socket.bind(addr, port): Socket    -- Create bound socket
```

### Socket Methods

```lua
socket:connect(address: string, port: u16)
socket:bind(address: string, port: u16)
socket:listen(backlog: s32 = 1)
socket:accept(): Socket
socket:send(data: string, i: s32 = 1, j: s32 = -1): s32
socket:receive(maxBytes: s32 = 0): string
socket:hasdata(): bool
socket:add(event: string, callback: function): s64
socket:remove(cbid: s64)
socket:poll()
socket:close()
```

### Socket Events

- `received` - Data available to read
- `error` - Error occurred

---

## MemoryDomain

Accessed via `emu.memory[name]` (e.g., `emu.memory.iwram`).

```lua
domain:name(): string
domain:base(): u32
domain:bound(): u32
domain:size(): u32
domain:read8(address: u32): u32
domain:read16(address: u32): u32
domain:read32(address: u32): u32
domain:write8(address: u32, value: u8)
domain:write16(address: u32, value: u16)
domain:write32(address: u32, value: u32)
domain:readRange(address: u32, length: u32): string
```

---

## Console Methods

```lua
console:log(msg: string)
console:warn(msg: string)
console:error(msg: string)
console:createBuffer(name: string): TextBuffer
```

### TextBuffer Methods

```lua
buffer:print(text: string)
buffer:clear()
buffer:moveCursor(x: s32, y: s32)
buffer:advance(adv: s32)
buffer:getX(): s32
buffer:getY(): s32
buffer:cols(): s32
buffer:rows(): s32
buffer:setSize(cols: s32, rows: s32)
buffer:setName(name: string)
```

---

## Example: Memory Watchpoint

```lua
-- Watch for player position changes
local WRITE_CHANGE = 5  -- or C.WATCHPOINT_TYPE.WRITE_CHANGE

local function onPlayerMove()
    local x = emu:read16(0x02036E38)
    local y = emu:read16(0x02036E3A)
    console:log("Player moved to " .. x .. ", " .. y)
end

-- Set watchpoint (returns ID for cleanup)
local watchId = emu:setWatchpoint(onPlayerMove, 0x02036E38, WRITE_CHANGE)

-- Later: clean up
emu:clearBreakpoint(watchId)
```

---

## Notes

1. **WATCHPOINT_TYPE.WRITE_CHANGE (5)** is the recommended type for most use cases - it only fires when the value actually changes, not on every write.

2. **setRangeWatchpoint** can watch a range of addresses but the end is exclusive.

3. **Watchpoint callbacks** receive no parameters - read the value inside the callback.

4. **Socket polling** happens automatically when using `add()` for events. Use `poll()` only for manual checking.

5. **State flags** default to SAVEDATA + CHEATS + RTC + METADATA (29) for load, ALL (31) for save.
