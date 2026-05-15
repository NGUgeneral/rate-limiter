-- rate_limiter.lua
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local nonce = ARGV[3]

-- Get Redis time (returns [seconds, microseconds])
local redis_time = redis.call('TIME')
local now = tonumber(redis_time[1])
local now_ms = tonumber(redis_time[2])
local current_ts = now + (now_ms / 1000000)
local window_start = current_ts - window

-- 1. Remove expired timestamps
redis.call('ZREMRANGEBYSCORE', key, 0, window_start)

-- 2. Count current requests
local current_count = redis.call('ZCARD', key)

if current_count < limit then
    -- 3. Add current request
    local member = current_ts .. ":" .. nonce
    redis.call('ZADD', key, current_ts, member)
    redis.call('EXPIRE', key, window)
    return {1, current_count + 1} -- Allowed, New Count
else
    return {0, current_count} -- Denied, Current Count
end