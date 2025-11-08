# Performance Guide

## Performance Benchmarking & Optimization

This document describes performance characteristics, benchmarking tools, and optimization strategies for LocalizationTools.

---

## 📊 Current Performance Metrics

### Memory Usage (Profiled)

**Database Operations:**
- Initialization: ~30 MB peak
- Runtime: ~27 MB steady state
- Per query: ~6-10 KB additional
- **Assessment: ✅ Excellent** (lightweight footprint)

**SQLAlchemy ORM:**
- Schema loading: ~240 KB
- Connection pool: ~120 KB
- Query overhead: minimal (<10 KB per query)

### Expected Performance Targets

**API Response Times:**
- Health check: <50ms (target <25ms)
- Authentication: <100ms (JWT validation)
- Log submission: <200ms (batch processing)
- Statistics queries: <500ms (aggregated data)

**Throughput:**
- Concurrent requests: >100 req/s
- Database connections: 10-50 concurrent
- Log batch size: up to 1000 entries

---

## 🛠️ Performance Tools

### 1. Server Benchmark (`scripts/benchmark_server.py`)

Comprehensive server performance testing.

**Features:**
- Sequential request testing (measure individual endpoint performance)
- Concurrent request testing (measure throughput under load)
- Response time statistics (min, max, avg, median, p95, p99)
- Requests per second calculation
- Error rate tracking

**Usage:**
```bash
# Start server first
python3 server/main.py

# In another terminal, run benchmark
python3 scripts/benchmark_server.py
```

**Tests Performed:**
1. Health check endpoint (100 sequential requests)
2. Root endpoint (100 sequential requests)
3. Version endpoint (100 sequential requests)
4. Announcements (100 sequential requests)
5. Concurrent health checks (10 workers × 20 requests)
6. Concurrent root endpoint (20 workers × 10 requests)

**Interpreting Results:**
- **<50ms avg**: Excellent performance ✅
- **50-100ms avg**: Good performance ✓
- **100-200ms avg**: Acceptable performance ⚠️
- **>200ms avg**: Needs optimization ❌

### 2. Memory Profiler (`scripts/profile_memory.py`)

Memory usage analysis for different components.

**Features:**
- Database operation profiling
- Module import profiling
- Peak memory tracking
- Memory allocation hotspots

**Usage:**
```bash
python3 scripts/profile_memory.py
```

**Analysis:**
- Database setup: ~30 MB (one-time cost)
- Runtime overhead: ~27 MB steady state
- Query overhead: ~6-10 KB per query

---

## ⚡ Optimization Strategies

### Database Optimization

**1. Connection Pooling**
```python
# Already configured in server/config.py
DB_POOL_SIZE = 5          # Concurrent connections
DB_MAX_OVERFLOW = 10      # Additional connections when needed
DB_POOL_RECYCLE = 3600    # Recycle connections every hour
```

**2. Query Optimization**
- Use `.filter()` instead of Python filtering
- Add indexes for frequently queried fields
- Use `limit()` for large result sets
- Batch inserts when possible

**3. Lazy Loading**
- SQLAlchemy models use lazy loading by default
- Relationships load on demand
- Use `joinedload()` for eager loading if needed

### API Performance

**1. Response Caching (Future)**
- Cache static data (version, announcements)
- Use Redis for distributed caching
- Set appropriate cache TTLs

**2. Async Processing (Future)**
- Background tasks for slow operations
- Celery/RQ for task queues
- Async endpoints for I/O-bound operations

**3. Request Validation**
- Pydantic models validate at edge
- Fast failing for invalid requests
- Minimize database hits for bad requests

### Client Performance

**1. Batch Operations**
- Batch log submissions (not one-by-one)
- Queue logs locally, flush periodically
- Reduce network overhead

**2. Progress Tracking**
- Lightweight progress updates
- Update UI every N iterations (not every item)
- Use `tqdm` for efficiency

**3. File Operations**
- Stream large files (don't load all in memory)
- Use generators where possible
- Clean up temp files promptly

---

## 📈 Performance Monitoring

### Metrics to Track

**Server Metrics:**
- Response time per endpoint
- Requests per second
- Error rate
- Active connections
- Memory usage
- CPU usage

**Database Metrics:**
- Query execution time
- Connection pool usage
- Lock contention
- Index usage
- Cache hit rate

**Client Metrics:**
- Operation duration
- File processing speed
- Network latency
- Queue depth

### Logging Performance Data

All operations are logged with duration:
```python
from client.utils.logger import get_logger

logger = get_logger()

@logger.log_operation(tool_name="XLSTransfer", function_name="create_dictionary")
def create_dictionary():
    # Function automatically logged with duration
    pass
```

Logs are stored in `server/database` and can be queried for performance analysis.

---

## 🎯 Performance Benchmarks

### Baseline Performance (Empty Database)

| Endpoint | Avg Response (ms) | Throughput (req/s) |
|----------|------------------|-------------------|
| Health Check | <25 | >200 |
| Root | <25 | >200 |
| Login | <100 | >50 |
| Log Submission | <200 | >30 |
| Statistics | <500 | >10 |

### Expected Performance (Production Load)

**Assumptions:**
- 50 active users
- 1000 operations/day
- Database size: <100MB

| Endpoint | Avg Response (ms) | Throughput (req/s) |
|----------|------------------|-------------------|
| Health Check | <50 | >100 |
| Root | <50 | >100 |
| Login | <150 | >30 |
| Log Submission | <300 | >20 |
| Statistics | <1000 | >5 |

---

## 🔧 Troubleshooting Performance Issues

### Slow API Responses

**Check:**
1. Database connection pool exhaustion
   - Solution: Increase `DB_POOL_SIZE`
2. Slow queries
   - Solution: Add indexes, optimize queries
3. Network latency
   - Solution: Check network configuration

### High Memory Usage

**Check:**
1. Database connection leaks
   - Solution: Ensure sessions are closed
2. Large result sets
   - Solution: Add pagination, use `limit()`
3. Caching too much data
   - Solution: Implement cache eviction

### Database Locks

**Check:**
1. Long-running transactions
   - Solution: Keep transactions short
2. Concurrent writes
   - Solution: Use optimistic locking
3. Missing indexes
   - Solution: Add indexes for WHERE clauses

---

## 📊 Future Optimizations

### Phase 1 (Current MVP)
- ✅ Connection pooling configured
- ✅ Efficient ORM queries
- ✅ Batch log submissions
- ✅ Memory profiling tools

### Phase 2 (Next Release)
- Response caching (Redis)
- Async endpoints (FastAPI async)
- Database query optimization (indexes)
- Background task processing (Celery)

### Phase 3 (Production Scale)
- Load balancing (multiple servers)
- Database read replicas
- CDN for static assets
- Full-text search (Elasticsearch)

---

## 📝 Performance Testing Checklist

Before each release:
- [ ] Run `scripts/benchmark_server.py`
- [ ] Run `scripts/profile_memory.py`
- [ ] Check all endpoints <500ms
- [ ] Verify throughput >20 req/s
- [ ] Test with realistic data load
- [ ] Monitor memory usage <100MB
- [ ] Check database query performance
- [ ] Review logs for slow operations

---

## 🎓 Best Practices

### Code Level
1. **Use connection pooling** - Don't create new connections per request
2. **Close sessions properly** - Use context managers or finally blocks
3. **Batch operations** - Group related operations together
4. **Lazy load relationships** - Load data only when needed
5. **Use generators** - For large data processing

### Database Level
1. **Add indexes** - On frequently queried columns
2. **Use transactions** - For multiple related writes
3. **Normalize data** - Reduce redundancy
4. **Regular maintenance** - VACUUM, ANALYZE for PostgreSQL

### API Level
1. **Validate early** - Reject bad requests fast
2. **Use pagination** - For large result sets
3. **Cache responses** - For static or slow data
4. **Compress responses** - Enable gzip compression
5. **Rate limiting** - Prevent abuse

---

## 📊 Monitoring Dashboard (Future)

Planned performance metrics in admin dashboard:
- Real-time response time graphs
- Request rate per endpoint
- Error rate trends
- Database query performance
- Memory and CPU usage
- Slow query log

---

## Summary

**Current State:**
- ✅ Lightweight memory footprint (~27 MB)
- ✅ Efficient database operations
- ✅ Performance monitoring tools ready
- ✅ Scalable architecture

**Performance is optimized for MVP scale (1-100 users).**
**Ready for production deployment with monitoring.**
