// Remote Logger - Send browser console logs to backend

const BACKEND_URL = 'http://localhost:8888';

// Store original console methods
const originalConsoleError = console.error;
const originalConsoleWarn = console.warn;

export const remoteLogger = {
  async log(level, message, data = {}) {
    // Log to console using original method
    if (level === 'ERROR') {
      originalConsoleError(`[${level}]`, message, data);
    } else if (level === 'WARNING') {
      originalConsoleWarn(`[${level}]`, message, data);
    } else {
      console.log(`[${level}]`, message, data);
    }

    // Send to backend
    try {
      await fetch(`${BACKEND_URL}/api/v1/remote-logs/frontend`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          level,
          message,
          data,
          timestamp: new Date().toISOString(),
          source: 'locanext-browser'
        })
      });
    } catch (err) {
      // Fail silently - don't break app if logging fails
    }
  },

  info(message, data) {
    return this.log('INFO', message, data);
  },

  success(message, data) {
    return this.log('SUCCESS', message, data);
  },

  error(message, data) {
    return this.log('ERROR', message, data);
  },

  warning(message, data) {
    return this.log('WARNING', message, data);
  },

  // Initialize global error handlers
  init() {
    // Capture window errors
    window.addEventListener('error', (event) => {
      this.error('Window Error', {
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        error: event.error?.stack
      });
    });

    // Capture unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      this.error('Unhandled Promise Rejection', {
        reason: event.reason,
        promise: event.promise
      });
    });

    // Intercept console.error
    console.error = (...args) => {
      // Filter out known non-critical errors
      const errorStr = args.map(arg => String(arg)).join(' ');

      // Skip WebSocket/Socket.IO connection errors (expected when not using WebSocket features)
      if (errorStr.includes('WebSocket connection error') ||
          errorStr.includes('TransportError')) {
        originalConsoleError.apply(console, args);
        return;
      }

      // UI-075 FIX: Properly serialize Error objects
      this.error('Console Error', {
        args: args.map(arg => {
          if (arg instanceof Error) {
            return { message: arg.message, stack: arg.stack, name: arg.name };
          } else if (typeof arg === 'object' && arg !== null) {
            try {
              return JSON.stringify(arg);
            } catch {
              return String(arg);
            }
          }
          return String(arg);
        })
      });
      originalConsoleError.apply(console, args);
    };

    // Intercept console.warn
    console.warn = (...args) => {
      this.warning('Console Warning', {
        args: args.map(arg =>
          typeof arg === 'object' ? JSON.stringify(arg) : String(arg)
        )
      });
      originalConsoleWarn.apply(console, args);
    };

    this.info('Remote logger initialized with global error handlers');
  }
};
