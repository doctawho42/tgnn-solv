(() => {
  var __create = Object.create;
  var __defProp = Object.defineProperty;
  var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __getProtoOf = Object.getPrototypeOf;
  var __hasOwnProp = Object.prototype.hasOwnProperty;
  var __commonJS = (cb, mod) => function __require() {
    return mod || (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod), mod.exports;
  };
  var __copyProps = (to, from, except, desc) => {
    if (from && typeof from === "object" || typeof from === "function") {
      for (let key of __getOwnPropNames(from))
        if (!__hasOwnProp.call(to, key) && key !== except)
          __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
    }
    return to;
  };
  var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
    // If the importer is in node compatibility mode or this is not an ESM
    // file that has been converted to a CommonJS file using a Babel-
    // compatible transform (i.e. "__esModule" has not been set), then set
    // "default" to the CommonJS "module.exports" for node compatibility.
    isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
    mod
  ));

  // node_modules/react/cjs/react.production.min.js
  var require_react_production_min = __commonJS({
    "node_modules/react/cjs/react.production.min.js"(exports) {
      "use strict";
      var l = Symbol.for("react.element");
      var n = Symbol.for("react.portal");
      var p = Symbol.for("react.fragment");
      var q = Symbol.for("react.strict_mode");
      var r = Symbol.for("react.profiler");
      var t = Symbol.for("react.provider");
      var u = Symbol.for("react.context");
      var v = Symbol.for("react.forward_ref");
      var w = Symbol.for("react.suspense");
      var x = Symbol.for("react.memo");
      var y = Symbol.for("react.lazy");
      var z = Symbol.iterator;
      function A(a) {
        if (null === a || "object" !== typeof a) return null;
        a = z && a[z] || a["@@iterator"];
        return "function" === typeof a ? a : null;
      }
      var B = { isMounted: function() {
        return false;
      }, enqueueForceUpdate: function() {
      }, enqueueReplaceState: function() {
      }, enqueueSetState: function() {
      } };
      var C = Object.assign;
      var D = {};
      function E(a, b, e) {
        this.props = a;
        this.context = b;
        this.refs = D;
        this.updater = e || B;
      }
      E.prototype.isReactComponent = {};
      E.prototype.setState = function(a, b) {
        if ("object" !== typeof a && "function" !== typeof a && null != a) throw Error("setState(...): takes an object of state variables to update or a function which returns an object of state variables.");
        this.updater.enqueueSetState(this, a, b, "setState");
      };
      E.prototype.forceUpdate = function(a) {
        this.updater.enqueueForceUpdate(this, a, "forceUpdate");
      };
      function F() {
      }
      F.prototype = E.prototype;
      function G(a, b, e) {
        this.props = a;
        this.context = b;
        this.refs = D;
        this.updater = e || B;
      }
      var H = G.prototype = new F();
      H.constructor = G;
      C(H, E.prototype);
      H.isPureReactComponent = true;
      var I = Array.isArray;
      var J = Object.prototype.hasOwnProperty;
      var K = { current: null };
      var L = { key: true, ref: true, __self: true, __source: true };
      function M(a, b, e) {
        var d, c = {}, k = null, h = null;
        if (null != b) for (d in void 0 !== b.ref && (h = b.ref), void 0 !== b.key && (k = "" + b.key), b) J.call(b, d) && !L.hasOwnProperty(d) && (c[d] = b[d]);
        var g = arguments.length - 2;
        if (1 === g) c.children = e;
        else if (1 < g) {
          for (var f = Array(g), m = 0; m < g; m++) f[m] = arguments[m + 2];
          c.children = f;
        }
        if (a && a.defaultProps) for (d in g = a.defaultProps, g) void 0 === c[d] && (c[d] = g[d]);
        return { $$typeof: l, type: a, key: k, ref: h, props: c, _owner: K.current };
      }
      function N(a, b) {
        return { $$typeof: l, type: a.type, key: b, ref: a.ref, props: a.props, _owner: a._owner };
      }
      function O(a) {
        return "object" === typeof a && null !== a && a.$$typeof === l;
      }
      function escape(a) {
        var b = { "=": "=0", ":": "=2" };
        return "$" + a.replace(/[=:]/g, function(a2) {
          return b[a2];
        });
      }
      var P = /\/+/g;
      function Q(a, b) {
        return "object" === typeof a && null !== a && null != a.key ? escape("" + a.key) : b.toString(36);
      }
      function R(a, b, e, d, c) {
        var k = typeof a;
        if ("undefined" === k || "boolean" === k) a = null;
        var h = false;
        if (null === a) h = true;
        else switch (k) {
          case "string":
          case "number":
            h = true;
            break;
          case "object":
            switch (a.$$typeof) {
              case l:
              case n:
                h = true;
            }
        }
        if (h) return h = a, c = c(h), a = "" === d ? "." + Q(h, 0) : d, I(c) ? (e = "", null != a && (e = a.replace(P, "$&/") + "/"), R(c, b, e, "", function(a2) {
          return a2;
        })) : null != c && (O(c) && (c = N(c, e + (!c.key || h && h.key === c.key ? "" : ("" + c.key).replace(P, "$&/") + "/") + a)), b.push(c)), 1;
        h = 0;
        d = "" === d ? "." : d + ":";
        if (I(a)) for (var g = 0; g < a.length; g++) {
          k = a[g];
          var f = d + Q(k, g);
          h += R(k, b, e, f, c);
        }
        else if (f = A(a), "function" === typeof f) for (a = f.call(a), g = 0; !(k = a.next()).done; ) k = k.value, f = d + Q(k, g++), h += R(k, b, e, f, c);
        else if ("object" === k) throw b = String(a), Error("Objects are not valid as a React child (found: " + ("[object Object]" === b ? "object with keys {" + Object.keys(a).join(", ") + "}" : b) + "). If you meant to render a collection of children, use an array instead.");
        return h;
      }
      function S(a, b, e) {
        if (null == a) return a;
        var d = [], c = 0;
        R(a, d, "", "", function(a2) {
          return b.call(e, a2, c++);
        });
        return d;
      }
      function T(a) {
        if (-1 === a._status) {
          var b = a._result;
          b = b();
          b.then(function(b2) {
            if (0 === a._status || -1 === a._status) a._status = 1, a._result = b2;
          }, function(b2) {
            if (0 === a._status || -1 === a._status) a._status = 2, a._result = b2;
          });
          -1 === a._status && (a._status = 0, a._result = b);
        }
        if (1 === a._status) return a._result.default;
        throw a._result;
      }
      var U = { current: null };
      var V = { transition: null };
      var W = { ReactCurrentDispatcher: U, ReactCurrentBatchConfig: V, ReactCurrentOwner: K };
      function X() {
        throw Error("act(...) is not supported in production builds of React.");
      }
      exports.Children = { map: S, forEach: function(a, b, e) {
        S(a, function() {
          b.apply(this, arguments);
        }, e);
      }, count: function(a) {
        var b = 0;
        S(a, function() {
          b++;
        });
        return b;
      }, toArray: function(a) {
        return S(a, function(a2) {
          return a2;
        }) || [];
      }, only: function(a) {
        if (!O(a)) throw Error("React.Children.only expected to receive a single React element child.");
        return a;
      } };
      exports.Component = E;
      exports.Fragment = p;
      exports.Profiler = r;
      exports.PureComponent = G;
      exports.StrictMode = q;
      exports.Suspense = w;
      exports.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED = W;
      exports.act = X;
      exports.cloneElement = function(a, b, e) {
        if (null === a || void 0 === a) throw Error("React.cloneElement(...): The argument must be a React element, but you passed " + a + ".");
        var d = C({}, a.props), c = a.key, k = a.ref, h = a._owner;
        if (null != b) {
          void 0 !== b.ref && (k = b.ref, h = K.current);
          void 0 !== b.key && (c = "" + b.key);
          if (a.type && a.type.defaultProps) var g = a.type.defaultProps;
          for (f in b) J.call(b, f) && !L.hasOwnProperty(f) && (d[f] = void 0 === b[f] && void 0 !== g ? g[f] : b[f]);
        }
        var f = arguments.length - 2;
        if (1 === f) d.children = e;
        else if (1 < f) {
          g = Array(f);
          for (var m = 0; m < f; m++) g[m] = arguments[m + 2];
          d.children = g;
        }
        return { $$typeof: l, type: a.type, key: c, ref: k, props: d, _owner: h };
      };
      exports.createContext = function(a) {
        a = { $$typeof: u, _currentValue: a, _currentValue2: a, _threadCount: 0, Provider: null, Consumer: null, _defaultValue: null, _globalName: null };
        a.Provider = { $$typeof: t, _context: a };
        return a.Consumer = a;
      };
      exports.createElement = M;
      exports.createFactory = function(a) {
        var b = M.bind(null, a);
        b.type = a;
        return b;
      };
      exports.createRef = function() {
        return { current: null };
      };
      exports.forwardRef = function(a) {
        return { $$typeof: v, render: a };
      };
      exports.isValidElement = O;
      exports.lazy = function(a) {
        return { $$typeof: y, _payload: { _status: -1, _result: a }, _init: T };
      };
      exports.memo = function(a, b) {
        return { $$typeof: x, type: a, compare: void 0 === b ? null : b };
      };
      exports.startTransition = function(a) {
        var b = V.transition;
        V.transition = {};
        try {
          a();
        } finally {
          V.transition = b;
        }
      };
      exports.unstable_act = X;
      exports.useCallback = function(a, b) {
        return U.current.useCallback(a, b);
      };
      exports.useContext = function(a) {
        return U.current.useContext(a);
      };
      exports.useDebugValue = function() {
      };
      exports.useDeferredValue = function(a) {
        return U.current.useDeferredValue(a);
      };
      exports.useEffect = function(a, b) {
        return U.current.useEffect(a, b);
      };
      exports.useId = function() {
        return U.current.useId();
      };
      exports.useImperativeHandle = function(a, b, e) {
        return U.current.useImperativeHandle(a, b, e);
      };
      exports.useInsertionEffect = function(a, b) {
        return U.current.useInsertionEffect(a, b);
      };
      exports.useLayoutEffect = function(a, b) {
        return U.current.useLayoutEffect(a, b);
      };
      exports.useMemo = function(a, b) {
        return U.current.useMemo(a, b);
      };
      exports.useReducer = function(a, b, e) {
        return U.current.useReducer(a, b, e);
      };
      exports.useRef = function(a) {
        return U.current.useRef(a);
      };
      exports.useState = function(a) {
        return U.current.useState(a);
      };
      exports.useSyncExternalStore = function(a, b, e) {
        return U.current.useSyncExternalStore(a, b, e);
      };
      exports.useTransition = function() {
        return U.current.useTransition();
      };
      exports.version = "18.3.1";
    }
  });

  // node_modules/react/index.js
  var require_react = __commonJS({
    "node_modules/react/index.js"(exports, module) {
      "use strict";
      if (true) {
        module.exports = require_react_production_min();
      } else {
        module.exports = null;
      }
    }
  });

  // node_modules/scheduler/cjs/scheduler.production.min.js
  var require_scheduler_production_min = __commonJS({
    "node_modules/scheduler/cjs/scheduler.production.min.js"(exports) {
      "use strict";
      function f(a, b) {
        var c = a.length;
        a.push(b);
        a: for (; 0 < c; ) {
          var d = c - 1 >>> 1, e = a[d];
          if (0 < g(e, b)) a[d] = b, a[c] = e, c = d;
          else break a;
        }
      }
      function h(a) {
        return 0 === a.length ? null : a[0];
      }
      function k(a) {
        if (0 === a.length) return null;
        var b = a[0], c = a.pop();
        if (c !== b) {
          a[0] = c;
          a: for (var d = 0, e = a.length, w = e >>> 1; d < w; ) {
            var m = 2 * (d + 1) - 1, C = a[m], n = m + 1, x = a[n];
            if (0 > g(C, c)) n < e && 0 > g(x, C) ? (a[d] = x, a[n] = c, d = n) : (a[d] = C, a[m] = c, d = m);
            else if (n < e && 0 > g(x, c)) a[d] = x, a[n] = c, d = n;
            else break a;
          }
        }
        return b;
      }
      function g(a, b) {
        var c = a.sortIndex - b.sortIndex;
        return 0 !== c ? c : a.id - b.id;
      }
      if ("object" === typeof performance && "function" === typeof performance.now) {
        l = performance;
        exports.unstable_now = function() {
          return l.now();
        };
      } else {
        p = Date, q = p.now();
        exports.unstable_now = function() {
          return p.now() - q;
        };
      }
      var l;
      var p;
      var q;
      var r = [];
      var t = [];
      var u = 1;
      var v = null;
      var y = 3;
      var z = false;
      var A = false;
      var B = false;
      var D = "function" === typeof setTimeout ? setTimeout : null;
      var E = "function" === typeof clearTimeout ? clearTimeout : null;
      var F = "undefined" !== typeof setImmediate ? setImmediate : null;
      "undefined" !== typeof navigator && void 0 !== navigator.scheduling && void 0 !== navigator.scheduling.isInputPending && navigator.scheduling.isInputPending.bind(navigator.scheduling);
      function G(a) {
        for (var b = h(t); null !== b; ) {
          if (null === b.callback) k(t);
          else if (b.startTime <= a) k(t), b.sortIndex = b.expirationTime, f(r, b);
          else break;
          b = h(t);
        }
      }
      function H(a) {
        B = false;
        G(a);
        if (!A) if (null !== h(r)) A = true, I(J);
        else {
          var b = h(t);
          null !== b && K(H, b.startTime - a);
        }
      }
      function J(a, b) {
        A = false;
        B && (B = false, E(L), L = -1);
        z = true;
        var c = y;
        try {
          G(b);
          for (v = h(r); null !== v && (!(v.expirationTime > b) || a && !M()); ) {
            var d = v.callback;
            if ("function" === typeof d) {
              v.callback = null;
              y = v.priorityLevel;
              var e = d(v.expirationTime <= b);
              b = exports.unstable_now();
              "function" === typeof e ? v.callback = e : v === h(r) && k(r);
              G(b);
            } else k(r);
            v = h(r);
          }
          if (null !== v) var w = true;
          else {
            var m = h(t);
            null !== m && K(H, m.startTime - b);
            w = false;
          }
          return w;
        } finally {
          v = null, y = c, z = false;
        }
      }
      var N = false;
      var O = null;
      var L = -1;
      var P = 5;
      var Q = -1;
      function M() {
        return exports.unstable_now() - Q < P ? false : true;
      }
      function R() {
        if (null !== O) {
          var a = exports.unstable_now();
          Q = a;
          var b = true;
          try {
            b = O(true, a);
          } finally {
            b ? S() : (N = false, O = null);
          }
        } else N = false;
      }
      var S;
      if ("function" === typeof F) S = function() {
        F(R);
      };
      else if ("undefined" !== typeof MessageChannel) {
        T = new MessageChannel(), U = T.port2;
        T.port1.onmessage = R;
        S = function() {
          U.postMessage(null);
        };
      } else S = function() {
        D(R, 0);
      };
      var T;
      var U;
      function I(a) {
        O = a;
        N || (N = true, S());
      }
      function K(a, b) {
        L = D(function() {
          a(exports.unstable_now());
        }, b);
      }
      exports.unstable_IdlePriority = 5;
      exports.unstable_ImmediatePriority = 1;
      exports.unstable_LowPriority = 4;
      exports.unstable_NormalPriority = 3;
      exports.unstable_Profiling = null;
      exports.unstable_UserBlockingPriority = 2;
      exports.unstable_cancelCallback = function(a) {
        a.callback = null;
      };
      exports.unstable_continueExecution = function() {
        A || z || (A = true, I(J));
      };
      exports.unstable_forceFrameRate = function(a) {
        0 > a || 125 < a ? console.error("forceFrameRate takes a positive int between 0 and 125, forcing frame rates higher than 125 fps is not supported") : P = 0 < a ? Math.floor(1e3 / a) : 5;
      };
      exports.unstable_getCurrentPriorityLevel = function() {
        return y;
      };
      exports.unstable_getFirstCallbackNode = function() {
        return h(r);
      };
      exports.unstable_next = function(a) {
        switch (y) {
          case 1:
          case 2:
          case 3:
            var b = 3;
            break;
          default:
            b = y;
        }
        var c = y;
        y = b;
        try {
          return a();
        } finally {
          y = c;
        }
      };
      exports.unstable_pauseExecution = function() {
      };
      exports.unstable_requestPaint = function() {
      };
      exports.unstable_runWithPriority = function(a, b) {
        switch (a) {
          case 1:
          case 2:
          case 3:
          case 4:
          case 5:
            break;
          default:
            a = 3;
        }
        var c = y;
        y = a;
        try {
          return b();
        } finally {
          y = c;
        }
      };
      exports.unstable_scheduleCallback = function(a, b, c) {
        var d = exports.unstable_now();
        "object" === typeof c && null !== c ? (c = c.delay, c = "number" === typeof c && 0 < c ? d + c : d) : c = d;
        switch (a) {
          case 1:
            var e = -1;
            break;
          case 2:
            e = 250;
            break;
          case 5:
            e = 1073741823;
            break;
          case 4:
            e = 1e4;
            break;
          default:
            e = 5e3;
        }
        e = c + e;
        a = { id: u++, callback: b, priorityLevel: a, startTime: c, expirationTime: e, sortIndex: -1 };
        c > d ? (a.sortIndex = c, f(t, a), null === h(r) && a === h(t) && (B ? (E(L), L = -1) : B = true, K(H, c - d))) : (a.sortIndex = e, f(r, a), A || z || (A = true, I(J)));
        return a;
      };
      exports.unstable_shouldYield = M;
      exports.unstable_wrapCallback = function(a) {
        var b = y;
        return function() {
          var c = y;
          y = b;
          try {
            return a.apply(this, arguments);
          } finally {
            y = c;
          }
        };
      };
    }
  });

  // node_modules/scheduler/index.js
  var require_scheduler = __commonJS({
    "node_modules/scheduler/index.js"(exports, module) {
      "use strict";
      if (true) {
        module.exports = require_scheduler_production_min();
      } else {
        module.exports = null;
      }
    }
  });

  // node_modules/react-dom/cjs/react-dom.production.min.js
  var require_react_dom_production_min = __commonJS({
    "node_modules/react-dom/cjs/react-dom.production.min.js"(exports) {
      "use strict";
      var aa = require_react();
      var ca = require_scheduler();
      function p(a) {
        for (var b = "https://reactjs.org/docs/error-decoder.html?invariant=" + a, c = 1; c < arguments.length; c++) b += "&args[]=" + encodeURIComponent(arguments[c]);
        return "Minified React error #" + a + "; visit " + b + " for the full message or use the non-minified dev environment for full errors and additional helpful warnings.";
      }
      var da = /* @__PURE__ */ new Set();
      var ea = {};
      function fa(a, b) {
        ha(a, b);
        ha(a + "Capture", b);
      }
      function ha(a, b) {
        ea[a] = b;
        for (a = 0; a < b.length; a++) da.add(b[a]);
      }
      var ia = !("undefined" === typeof window || "undefined" === typeof window.document || "undefined" === typeof window.document.createElement);
      var ja = Object.prototype.hasOwnProperty;
      var ka = /^[:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD][:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\-.0-9\u00B7\u0300-\u036F\u203F-\u2040]*$/;
      var la = {};
      var ma = {};
      function oa(a) {
        if (ja.call(ma, a)) return true;
        if (ja.call(la, a)) return false;
        if (ka.test(a)) return ma[a] = true;
        la[a] = true;
        return false;
      }
      function pa(a, b, c, d) {
        if (null !== c && 0 === c.type) return false;
        switch (typeof b) {
          case "function":
          case "symbol":
            return true;
          case "boolean":
            if (d) return false;
            if (null !== c) return !c.acceptsBooleans;
            a = a.toLowerCase().slice(0, 5);
            return "data-" !== a && "aria-" !== a;
          default:
            return false;
        }
      }
      function qa(a, b, c, d) {
        if (null === b || "undefined" === typeof b || pa(a, b, c, d)) return true;
        if (d) return false;
        if (null !== c) switch (c.type) {
          case 3:
            return !b;
          case 4:
            return false === b;
          case 5:
            return isNaN(b);
          case 6:
            return isNaN(b) || 1 > b;
        }
        return false;
      }
      function v(a, b, c, d, e, f, g) {
        this.acceptsBooleans = 2 === b || 3 === b || 4 === b;
        this.attributeName = d;
        this.attributeNamespace = e;
        this.mustUseProperty = c;
        this.propertyName = a;
        this.type = b;
        this.sanitizeURL = f;
        this.removeEmptyString = g;
      }
      var z = {};
      "children dangerouslySetInnerHTML defaultValue defaultChecked innerHTML suppressContentEditableWarning suppressHydrationWarning style".split(" ").forEach(function(a) {
        z[a] = new v(a, 0, false, a, null, false, false);
      });
      [["acceptCharset", "accept-charset"], ["className", "class"], ["htmlFor", "for"], ["httpEquiv", "http-equiv"]].forEach(function(a) {
        var b = a[0];
        z[b] = new v(b, 1, false, a[1], null, false, false);
      });
      ["contentEditable", "draggable", "spellCheck", "value"].forEach(function(a) {
        z[a] = new v(a, 2, false, a.toLowerCase(), null, false, false);
      });
      ["autoReverse", "externalResourcesRequired", "focusable", "preserveAlpha"].forEach(function(a) {
        z[a] = new v(a, 2, false, a, null, false, false);
      });
      "allowFullScreen async autoFocus autoPlay controls default defer disabled disablePictureInPicture disableRemotePlayback formNoValidate hidden loop noModule noValidate open playsInline readOnly required reversed scoped seamless itemScope".split(" ").forEach(function(a) {
        z[a] = new v(a, 3, false, a.toLowerCase(), null, false, false);
      });
      ["checked", "multiple", "muted", "selected"].forEach(function(a) {
        z[a] = new v(a, 3, true, a, null, false, false);
      });
      ["capture", "download"].forEach(function(a) {
        z[a] = new v(a, 4, false, a, null, false, false);
      });
      ["cols", "rows", "size", "span"].forEach(function(a) {
        z[a] = new v(a, 6, false, a, null, false, false);
      });
      ["rowSpan", "start"].forEach(function(a) {
        z[a] = new v(a, 5, false, a.toLowerCase(), null, false, false);
      });
      var ra = /[\-:]([a-z])/g;
      function sa(a) {
        return a[1].toUpperCase();
      }
      "accent-height alignment-baseline arabic-form baseline-shift cap-height clip-path clip-rule color-interpolation color-interpolation-filters color-profile color-rendering dominant-baseline enable-background fill-opacity fill-rule flood-color flood-opacity font-family font-size font-size-adjust font-stretch font-style font-variant font-weight glyph-name glyph-orientation-horizontal glyph-orientation-vertical horiz-adv-x horiz-origin-x image-rendering letter-spacing lighting-color marker-end marker-mid marker-start overline-position overline-thickness paint-order panose-1 pointer-events rendering-intent shape-rendering stop-color stop-opacity strikethrough-position strikethrough-thickness stroke-dasharray stroke-dashoffset stroke-linecap stroke-linejoin stroke-miterlimit stroke-opacity stroke-width text-anchor text-decoration text-rendering underline-position underline-thickness unicode-bidi unicode-range units-per-em v-alphabetic v-hanging v-ideographic v-mathematical vector-effect vert-adv-y vert-origin-x vert-origin-y word-spacing writing-mode xmlns:xlink x-height".split(" ").forEach(function(a) {
        var b = a.replace(
          ra,
          sa
        );
        z[b] = new v(b, 1, false, a, null, false, false);
      });
      "xlink:actuate xlink:arcrole xlink:role xlink:show xlink:title xlink:type".split(" ").forEach(function(a) {
        var b = a.replace(ra, sa);
        z[b] = new v(b, 1, false, a, "http://www.w3.org/1999/xlink", false, false);
      });
      ["xml:base", "xml:lang", "xml:space"].forEach(function(a) {
        var b = a.replace(ra, sa);
        z[b] = new v(b, 1, false, a, "http://www.w3.org/XML/1998/namespace", false, false);
      });
      ["tabIndex", "crossOrigin"].forEach(function(a) {
        z[a] = new v(a, 1, false, a.toLowerCase(), null, false, false);
      });
      z.xlinkHref = new v("xlinkHref", 1, false, "xlink:href", "http://www.w3.org/1999/xlink", true, false);
      ["src", "href", "action", "formAction"].forEach(function(a) {
        z[a] = new v(a, 1, false, a.toLowerCase(), null, true, true);
      });
      function ta(a, b, c, d) {
        var e = z.hasOwnProperty(b) ? z[b] : null;
        if (null !== e ? 0 !== e.type : d || !(2 < b.length) || "o" !== b[0] && "O" !== b[0] || "n" !== b[1] && "N" !== b[1]) qa(b, c, e, d) && (c = null), d || null === e ? oa(b) && (null === c ? a.removeAttribute(b) : a.setAttribute(b, "" + c)) : e.mustUseProperty ? a[e.propertyName] = null === c ? 3 === e.type ? false : "" : c : (b = e.attributeName, d = e.attributeNamespace, null === c ? a.removeAttribute(b) : (e = e.type, c = 3 === e || 4 === e && true === c ? "" : "" + c, d ? a.setAttributeNS(d, b, c) : a.setAttribute(b, c)));
      }
      var ua = aa.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED;
      var va = Symbol.for("react.element");
      var wa = Symbol.for("react.portal");
      var ya = Symbol.for("react.fragment");
      var za = Symbol.for("react.strict_mode");
      var Aa = Symbol.for("react.profiler");
      var Ba = Symbol.for("react.provider");
      var Ca = Symbol.for("react.context");
      var Da = Symbol.for("react.forward_ref");
      var Ea = Symbol.for("react.suspense");
      var Fa = Symbol.for("react.suspense_list");
      var Ga = Symbol.for("react.memo");
      var Ha = Symbol.for("react.lazy");
      Symbol.for("react.scope");
      Symbol.for("react.debug_trace_mode");
      var Ia = Symbol.for("react.offscreen");
      Symbol.for("react.legacy_hidden");
      Symbol.for("react.cache");
      Symbol.for("react.tracing_marker");
      var Ja = Symbol.iterator;
      function Ka(a) {
        if (null === a || "object" !== typeof a) return null;
        a = Ja && a[Ja] || a["@@iterator"];
        return "function" === typeof a ? a : null;
      }
      var A = Object.assign;
      var La;
      function Ma(a) {
        if (void 0 === La) try {
          throw Error();
        } catch (c) {
          var b = c.stack.trim().match(/\n( *(at )?)/);
          La = b && b[1] || "";
        }
        return "\n" + La + a;
      }
      var Na = false;
      function Oa(a, b) {
        if (!a || Na) return "";
        Na = true;
        var c = Error.prepareStackTrace;
        Error.prepareStackTrace = void 0;
        try {
          if (b) if (b = function() {
            throw Error();
          }, Object.defineProperty(b.prototype, "props", { set: function() {
            throw Error();
          } }), "object" === typeof Reflect && Reflect.construct) {
            try {
              Reflect.construct(b, []);
            } catch (l) {
              var d = l;
            }
            Reflect.construct(a, [], b);
          } else {
            try {
              b.call();
            } catch (l) {
              d = l;
            }
            a.call(b.prototype);
          }
          else {
            try {
              throw Error();
            } catch (l) {
              d = l;
            }
            a();
          }
        } catch (l) {
          if (l && d && "string" === typeof l.stack) {
            for (var e = l.stack.split("\n"), f = d.stack.split("\n"), g = e.length - 1, h = f.length - 1; 1 <= g && 0 <= h && e[g] !== f[h]; ) h--;
            for (; 1 <= g && 0 <= h; g--, h--) if (e[g] !== f[h]) {
              if (1 !== g || 1 !== h) {
                do
                  if (g--, h--, 0 > h || e[g] !== f[h]) {
                    var k = "\n" + e[g].replace(" at new ", " at ");
                    a.displayName && k.includes("<anonymous>") && (k = k.replace("<anonymous>", a.displayName));
                    return k;
                  }
                while (1 <= g && 0 <= h);
              }
              break;
            }
          }
        } finally {
          Na = false, Error.prepareStackTrace = c;
        }
        return (a = a ? a.displayName || a.name : "") ? Ma(a) : "";
      }
      function Pa(a) {
        switch (a.tag) {
          case 5:
            return Ma(a.type);
          case 16:
            return Ma("Lazy");
          case 13:
            return Ma("Suspense");
          case 19:
            return Ma("SuspenseList");
          case 0:
          case 2:
          case 15:
            return a = Oa(a.type, false), a;
          case 11:
            return a = Oa(a.type.render, false), a;
          case 1:
            return a = Oa(a.type, true), a;
          default:
            return "";
        }
      }
      function Qa(a) {
        if (null == a) return null;
        if ("function" === typeof a) return a.displayName || a.name || null;
        if ("string" === typeof a) return a;
        switch (a) {
          case ya:
            return "Fragment";
          case wa:
            return "Portal";
          case Aa:
            return "Profiler";
          case za:
            return "StrictMode";
          case Ea:
            return "Suspense";
          case Fa:
            return "SuspenseList";
        }
        if ("object" === typeof a) switch (a.$$typeof) {
          case Ca:
            return (a.displayName || "Context") + ".Consumer";
          case Ba:
            return (a._context.displayName || "Context") + ".Provider";
          case Da:
            var b = a.render;
            a = a.displayName;
            a || (a = b.displayName || b.name || "", a = "" !== a ? "ForwardRef(" + a + ")" : "ForwardRef");
            return a;
          case Ga:
            return b = a.displayName || null, null !== b ? b : Qa(a.type) || "Memo";
          case Ha:
            b = a._payload;
            a = a._init;
            try {
              return Qa(a(b));
            } catch (c) {
            }
        }
        return null;
      }
      function Ra(a) {
        var b = a.type;
        switch (a.tag) {
          case 24:
            return "Cache";
          case 9:
            return (b.displayName || "Context") + ".Consumer";
          case 10:
            return (b._context.displayName || "Context") + ".Provider";
          case 18:
            return "DehydratedFragment";
          case 11:
            return a = b.render, a = a.displayName || a.name || "", b.displayName || ("" !== a ? "ForwardRef(" + a + ")" : "ForwardRef");
          case 7:
            return "Fragment";
          case 5:
            return b;
          case 4:
            return "Portal";
          case 3:
            return "Root";
          case 6:
            return "Text";
          case 16:
            return Qa(b);
          case 8:
            return b === za ? "StrictMode" : "Mode";
          case 22:
            return "Offscreen";
          case 12:
            return "Profiler";
          case 21:
            return "Scope";
          case 13:
            return "Suspense";
          case 19:
            return "SuspenseList";
          case 25:
            return "TracingMarker";
          case 1:
          case 0:
          case 17:
          case 2:
          case 14:
          case 15:
            if ("function" === typeof b) return b.displayName || b.name || null;
            if ("string" === typeof b) return b;
        }
        return null;
      }
      function Sa(a) {
        switch (typeof a) {
          case "boolean":
          case "number":
          case "string":
          case "undefined":
            return a;
          case "object":
            return a;
          default:
            return "";
        }
      }
      function Ta(a) {
        var b = a.type;
        return (a = a.nodeName) && "input" === a.toLowerCase() && ("checkbox" === b || "radio" === b);
      }
      function Ua(a) {
        var b = Ta(a) ? "checked" : "value", c = Object.getOwnPropertyDescriptor(a.constructor.prototype, b), d = "" + a[b];
        if (!a.hasOwnProperty(b) && "undefined" !== typeof c && "function" === typeof c.get && "function" === typeof c.set) {
          var e = c.get, f = c.set;
          Object.defineProperty(a, b, { configurable: true, get: function() {
            return e.call(this);
          }, set: function(a2) {
            d = "" + a2;
            f.call(this, a2);
          } });
          Object.defineProperty(a, b, { enumerable: c.enumerable });
          return { getValue: function() {
            return d;
          }, setValue: function(a2) {
            d = "" + a2;
          }, stopTracking: function() {
            a._valueTracker = null;
            delete a[b];
          } };
        }
      }
      function Va(a) {
        a._valueTracker || (a._valueTracker = Ua(a));
      }
      function Wa(a) {
        if (!a) return false;
        var b = a._valueTracker;
        if (!b) return true;
        var c = b.getValue();
        var d = "";
        a && (d = Ta(a) ? a.checked ? "true" : "false" : a.value);
        a = d;
        return a !== c ? (b.setValue(a), true) : false;
      }
      function Xa(a) {
        a = a || ("undefined" !== typeof document ? document : void 0);
        if ("undefined" === typeof a) return null;
        try {
          return a.activeElement || a.body;
        } catch (b) {
          return a.body;
        }
      }
      function Ya(a, b) {
        var c = b.checked;
        return A({}, b, { defaultChecked: void 0, defaultValue: void 0, value: void 0, checked: null != c ? c : a._wrapperState.initialChecked });
      }
      function Za(a, b) {
        var c = null == b.defaultValue ? "" : b.defaultValue, d = null != b.checked ? b.checked : b.defaultChecked;
        c = Sa(null != b.value ? b.value : c);
        a._wrapperState = { initialChecked: d, initialValue: c, controlled: "checkbox" === b.type || "radio" === b.type ? null != b.checked : null != b.value };
      }
      function ab(a, b) {
        b = b.checked;
        null != b && ta(a, "checked", b, false);
      }
      function bb(a, b) {
        ab(a, b);
        var c = Sa(b.value), d = b.type;
        if (null != c) if ("number" === d) {
          if (0 === c && "" === a.value || a.value != c) a.value = "" + c;
        } else a.value !== "" + c && (a.value = "" + c);
        else if ("submit" === d || "reset" === d) {
          a.removeAttribute("value");
          return;
        }
        b.hasOwnProperty("value") ? cb(a, b.type, c) : b.hasOwnProperty("defaultValue") && cb(a, b.type, Sa(b.defaultValue));
        null == b.checked && null != b.defaultChecked && (a.defaultChecked = !!b.defaultChecked);
      }
      function db(a, b, c) {
        if (b.hasOwnProperty("value") || b.hasOwnProperty("defaultValue")) {
          var d = b.type;
          if (!("submit" !== d && "reset" !== d || void 0 !== b.value && null !== b.value)) return;
          b = "" + a._wrapperState.initialValue;
          c || b === a.value || (a.value = b);
          a.defaultValue = b;
        }
        c = a.name;
        "" !== c && (a.name = "");
        a.defaultChecked = !!a._wrapperState.initialChecked;
        "" !== c && (a.name = c);
      }
      function cb(a, b, c) {
        if ("number" !== b || Xa(a.ownerDocument) !== a) null == c ? a.defaultValue = "" + a._wrapperState.initialValue : a.defaultValue !== "" + c && (a.defaultValue = "" + c);
      }
      var eb = Array.isArray;
      function fb(a, b, c, d) {
        a = a.options;
        if (b) {
          b = {};
          for (var e = 0; e < c.length; e++) b["$" + c[e]] = true;
          for (c = 0; c < a.length; c++) e = b.hasOwnProperty("$" + a[c].value), a[c].selected !== e && (a[c].selected = e), e && d && (a[c].defaultSelected = true);
        } else {
          c = "" + Sa(c);
          b = null;
          for (e = 0; e < a.length; e++) {
            if (a[e].value === c) {
              a[e].selected = true;
              d && (a[e].defaultSelected = true);
              return;
            }
            null !== b || a[e].disabled || (b = a[e]);
          }
          null !== b && (b.selected = true);
        }
      }
      function gb(a, b) {
        if (null != b.dangerouslySetInnerHTML) throw Error(p(91));
        return A({}, b, { value: void 0, defaultValue: void 0, children: "" + a._wrapperState.initialValue });
      }
      function hb(a, b) {
        var c = b.value;
        if (null == c) {
          c = b.children;
          b = b.defaultValue;
          if (null != c) {
            if (null != b) throw Error(p(92));
            if (eb(c)) {
              if (1 < c.length) throw Error(p(93));
              c = c[0];
            }
            b = c;
          }
          null == b && (b = "");
          c = b;
        }
        a._wrapperState = { initialValue: Sa(c) };
      }
      function ib(a, b) {
        var c = Sa(b.value), d = Sa(b.defaultValue);
        null != c && (c = "" + c, c !== a.value && (a.value = c), null == b.defaultValue && a.defaultValue !== c && (a.defaultValue = c));
        null != d && (a.defaultValue = "" + d);
      }
      function jb(a) {
        var b = a.textContent;
        b === a._wrapperState.initialValue && "" !== b && null !== b && (a.value = b);
      }
      function kb(a) {
        switch (a) {
          case "svg":
            return "http://www.w3.org/2000/svg";
          case "math":
            return "http://www.w3.org/1998/Math/MathML";
          default:
            return "http://www.w3.org/1999/xhtml";
        }
      }
      function lb(a, b) {
        return null == a || "http://www.w3.org/1999/xhtml" === a ? kb(b) : "http://www.w3.org/2000/svg" === a && "foreignObject" === b ? "http://www.w3.org/1999/xhtml" : a;
      }
      var mb;
      var nb = (function(a) {
        return "undefined" !== typeof MSApp && MSApp.execUnsafeLocalFunction ? function(b, c, d, e) {
          MSApp.execUnsafeLocalFunction(function() {
            return a(b, c, d, e);
          });
        } : a;
      })(function(a, b) {
        if ("http://www.w3.org/2000/svg" !== a.namespaceURI || "innerHTML" in a) a.innerHTML = b;
        else {
          mb = mb || document.createElement("div");
          mb.innerHTML = "<svg>" + b.valueOf().toString() + "</svg>";
          for (b = mb.firstChild; a.firstChild; ) a.removeChild(a.firstChild);
          for (; b.firstChild; ) a.appendChild(b.firstChild);
        }
      });
      function ob(a, b) {
        if (b) {
          var c = a.firstChild;
          if (c && c === a.lastChild && 3 === c.nodeType) {
            c.nodeValue = b;
            return;
          }
        }
        a.textContent = b;
      }
      var pb = {
        animationIterationCount: true,
        aspectRatio: true,
        borderImageOutset: true,
        borderImageSlice: true,
        borderImageWidth: true,
        boxFlex: true,
        boxFlexGroup: true,
        boxOrdinalGroup: true,
        columnCount: true,
        columns: true,
        flex: true,
        flexGrow: true,
        flexPositive: true,
        flexShrink: true,
        flexNegative: true,
        flexOrder: true,
        gridArea: true,
        gridRow: true,
        gridRowEnd: true,
        gridRowSpan: true,
        gridRowStart: true,
        gridColumn: true,
        gridColumnEnd: true,
        gridColumnSpan: true,
        gridColumnStart: true,
        fontWeight: true,
        lineClamp: true,
        lineHeight: true,
        opacity: true,
        order: true,
        orphans: true,
        tabSize: true,
        widows: true,
        zIndex: true,
        zoom: true,
        fillOpacity: true,
        floodOpacity: true,
        stopOpacity: true,
        strokeDasharray: true,
        strokeDashoffset: true,
        strokeMiterlimit: true,
        strokeOpacity: true,
        strokeWidth: true
      };
      var qb = ["Webkit", "ms", "Moz", "O"];
      Object.keys(pb).forEach(function(a) {
        qb.forEach(function(b) {
          b = b + a.charAt(0).toUpperCase() + a.substring(1);
          pb[b] = pb[a];
        });
      });
      function rb(a, b, c) {
        return null == b || "boolean" === typeof b || "" === b ? "" : c || "number" !== typeof b || 0 === b || pb.hasOwnProperty(a) && pb[a] ? ("" + b).trim() : b + "px";
      }
      function sb(a, b) {
        a = a.style;
        for (var c in b) if (b.hasOwnProperty(c)) {
          var d = 0 === c.indexOf("--"), e = rb(c, b[c], d);
          "float" === c && (c = "cssFloat");
          d ? a.setProperty(c, e) : a[c] = e;
        }
      }
      var tb = A({ menuitem: true }, { area: true, base: true, br: true, col: true, embed: true, hr: true, img: true, input: true, keygen: true, link: true, meta: true, param: true, source: true, track: true, wbr: true });
      function ub(a, b) {
        if (b) {
          if (tb[a] && (null != b.children || null != b.dangerouslySetInnerHTML)) throw Error(p(137, a));
          if (null != b.dangerouslySetInnerHTML) {
            if (null != b.children) throw Error(p(60));
            if ("object" !== typeof b.dangerouslySetInnerHTML || !("__html" in b.dangerouslySetInnerHTML)) throw Error(p(61));
          }
          if (null != b.style && "object" !== typeof b.style) throw Error(p(62));
        }
      }
      function vb(a, b) {
        if (-1 === a.indexOf("-")) return "string" === typeof b.is;
        switch (a) {
          case "annotation-xml":
          case "color-profile":
          case "font-face":
          case "font-face-src":
          case "font-face-uri":
          case "font-face-format":
          case "font-face-name":
          case "missing-glyph":
            return false;
          default:
            return true;
        }
      }
      var wb = null;
      function xb(a) {
        a = a.target || a.srcElement || window;
        a.correspondingUseElement && (a = a.correspondingUseElement);
        return 3 === a.nodeType ? a.parentNode : a;
      }
      var yb = null;
      var zb = null;
      var Ab = null;
      function Bb(a) {
        if (a = Cb(a)) {
          if ("function" !== typeof yb) throw Error(p(280));
          var b = a.stateNode;
          b && (b = Db(b), yb(a.stateNode, a.type, b));
        }
      }
      function Eb(a) {
        zb ? Ab ? Ab.push(a) : Ab = [a] : zb = a;
      }
      function Fb() {
        if (zb) {
          var a = zb, b = Ab;
          Ab = zb = null;
          Bb(a);
          if (b) for (a = 0; a < b.length; a++) Bb(b[a]);
        }
      }
      function Gb(a, b) {
        return a(b);
      }
      function Hb() {
      }
      var Ib = false;
      function Jb(a, b, c) {
        if (Ib) return a(b, c);
        Ib = true;
        try {
          return Gb(a, b, c);
        } finally {
          if (Ib = false, null !== zb || null !== Ab) Hb(), Fb();
        }
      }
      function Kb(a, b) {
        var c = a.stateNode;
        if (null === c) return null;
        var d = Db(c);
        if (null === d) return null;
        c = d[b];
        a: switch (b) {
          case "onClick":
          case "onClickCapture":
          case "onDoubleClick":
          case "onDoubleClickCapture":
          case "onMouseDown":
          case "onMouseDownCapture":
          case "onMouseMove":
          case "onMouseMoveCapture":
          case "onMouseUp":
          case "onMouseUpCapture":
          case "onMouseEnter":
            (d = !d.disabled) || (a = a.type, d = !("button" === a || "input" === a || "select" === a || "textarea" === a));
            a = !d;
            break a;
          default:
            a = false;
        }
        if (a) return null;
        if (c && "function" !== typeof c) throw Error(p(231, b, typeof c));
        return c;
      }
      var Lb = false;
      if (ia) try {
        Mb = {};
        Object.defineProperty(Mb, "passive", { get: function() {
          Lb = true;
        } });
        window.addEventListener("test", Mb, Mb);
        window.removeEventListener("test", Mb, Mb);
      } catch (a) {
        Lb = false;
      }
      var Mb;
      function Nb(a, b, c, d, e, f, g, h, k) {
        var l = Array.prototype.slice.call(arguments, 3);
        try {
          b.apply(c, l);
        } catch (m) {
          this.onError(m);
        }
      }
      var Ob = false;
      var Pb = null;
      var Qb = false;
      var Rb = null;
      var Sb = { onError: function(a) {
        Ob = true;
        Pb = a;
      } };
      function Tb(a, b, c, d, e, f, g, h, k) {
        Ob = false;
        Pb = null;
        Nb.apply(Sb, arguments);
      }
      function Ub(a, b, c, d, e, f, g, h, k) {
        Tb.apply(this, arguments);
        if (Ob) {
          if (Ob) {
            var l = Pb;
            Ob = false;
            Pb = null;
          } else throw Error(p(198));
          Qb || (Qb = true, Rb = l);
        }
      }
      function Vb(a) {
        var b = a, c = a;
        if (a.alternate) for (; b.return; ) b = b.return;
        else {
          a = b;
          do
            b = a, 0 !== (b.flags & 4098) && (c = b.return), a = b.return;
          while (a);
        }
        return 3 === b.tag ? c : null;
      }
      function Wb(a) {
        if (13 === a.tag) {
          var b = a.memoizedState;
          null === b && (a = a.alternate, null !== a && (b = a.memoizedState));
          if (null !== b) return b.dehydrated;
        }
        return null;
      }
      function Xb(a) {
        if (Vb(a) !== a) throw Error(p(188));
      }
      function Yb(a) {
        var b = a.alternate;
        if (!b) {
          b = Vb(a);
          if (null === b) throw Error(p(188));
          return b !== a ? null : a;
        }
        for (var c = a, d = b; ; ) {
          var e = c.return;
          if (null === e) break;
          var f = e.alternate;
          if (null === f) {
            d = e.return;
            if (null !== d) {
              c = d;
              continue;
            }
            break;
          }
          if (e.child === f.child) {
            for (f = e.child; f; ) {
              if (f === c) return Xb(e), a;
              if (f === d) return Xb(e), b;
              f = f.sibling;
            }
            throw Error(p(188));
          }
          if (c.return !== d.return) c = e, d = f;
          else {
            for (var g = false, h = e.child; h; ) {
              if (h === c) {
                g = true;
                c = e;
                d = f;
                break;
              }
              if (h === d) {
                g = true;
                d = e;
                c = f;
                break;
              }
              h = h.sibling;
            }
            if (!g) {
              for (h = f.child; h; ) {
                if (h === c) {
                  g = true;
                  c = f;
                  d = e;
                  break;
                }
                if (h === d) {
                  g = true;
                  d = f;
                  c = e;
                  break;
                }
                h = h.sibling;
              }
              if (!g) throw Error(p(189));
            }
          }
          if (c.alternate !== d) throw Error(p(190));
        }
        if (3 !== c.tag) throw Error(p(188));
        return c.stateNode.current === c ? a : b;
      }
      function Zb(a) {
        a = Yb(a);
        return null !== a ? $b(a) : null;
      }
      function $b(a) {
        if (5 === a.tag || 6 === a.tag) return a;
        for (a = a.child; null !== a; ) {
          var b = $b(a);
          if (null !== b) return b;
          a = a.sibling;
        }
        return null;
      }
      var ac = ca.unstable_scheduleCallback;
      var bc = ca.unstable_cancelCallback;
      var cc = ca.unstable_shouldYield;
      var dc = ca.unstable_requestPaint;
      var B = ca.unstable_now;
      var ec = ca.unstable_getCurrentPriorityLevel;
      var fc = ca.unstable_ImmediatePriority;
      var gc = ca.unstable_UserBlockingPriority;
      var hc = ca.unstable_NormalPriority;
      var ic = ca.unstable_LowPriority;
      var jc = ca.unstable_IdlePriority;
      var kc = null;
      var lc = null;
      function mc(a) {
        if (lc && "function" === typeof lc.onCommitFiberRoot) try {
          lc.onCommitFiberRoot(kc, a, void 0, 128 === (a.current.flags & 128));
        } catch (b) {
        }
      }
      var oc = Math.clz32 ? Math.clz32 : nc;
      var pc = Math.log;
      var qc = Math.LN2;
      function nc(a) {
        a >>>= 0;
        return 0 === a ? 32 : 31 - (pc(a) / qc | 0) | 0;
      }
      var rc = 64;
      var sc = 4194304;
      function tc(a) {
        switch (a & -a) {
          case 1:
            return 1;
          case 2:
            return 2;
          case 4:
            return 4;
          case 8:
            return 8;
          case 16:
            return 16;
          case 32:
            return 32;
          case 64:
          case 128:
          case 256:
          case 512:
          case 1024:
          case 2048:
          case 4096:
          case 8192:
          case 16384:
          case 32768:
          case 65536:
          case 131072:
          case 262144:
          case 524288:
          case 1048576:
          case 2097152:
            return a & 4194240;
          case 4194304:
          case 8388608:
          case 16777216:
          case 33554432:
          case 67108864:
            return a & 130023424;
          case 134217728:
            return 134217728;
          case 268435456:
            return 268435456;
          case 536870912:
            return 536870912;
          case 1073741824:
            return 1073741824;
          default:
            return a;
        }
      }
      function uc(a, b) {
        var c = a.pendingLanes;
        if (0 === c) return 0;
        var d = 0, e = a.suspendedLanes, f = a.pingedLanes, g = c & 268435455;
        if (0 !== g) {
          var h = g & ~e;
          0 !== h ? d = tc(h) : (f &= g, 0 !== f && (d = tc(f)));
        } else g = c & ~e, 0 !== g ? d = tc(g) : 0 !== f && (d = tc(f));
        if (0 === d) return 0;
        if (0 !== b && b !== d && 0 === (b & e) && (e = d & -d, f = b & -b, e >= f || 16 === e && 0 !== (f & 4194240))) return b;
        0 !== (d & 4) && (d |= c & 16);
        b = a.entangledLanes;
        if (0 !== b) for (a = a.entanglements, b &= d; 0 < b; ) c = 31 - oc(b), e = 1 << c, d |= a[c], b &= ~e;
        return d;
      }
      function vc(a, b) {
        switch (a) {
          case 1:
          case 2:
          case 4:
            return b + 250;
          case 8:
          case 16:
          case 32:
          case 64:
          case 128:
          case 256:
          case 512:
          case 1024:
          case 2048:
          case 4096:
          case 8192:
          case 16384:
          case 32768:
          case 65536:
          case 131072:
          case 262144:
          case 524288:
          case 1048576:
          case 2097152:
            return b + 5e3;
          case 4194304:
          case 8388608:
          case 16777216:
          case 33554432:
          case 67108864:
            return -1;
          case 134217728:
          case 268435456:
          case 536870912:
          case 1073741824:
            return -1;
          default:
            return -1;
        }
      }
      function wc(a, b) {
        for (var c = a.suspendedLanes, d = a.pingedLanes, e = a.expirationTimes, f = a.pendingLanes; 0 < f; ) {
          var g = 31 - oc(f), h = 1 << g, k = e[g];
          if (-1 === k) {
            if (0 === (h & c) || 0 !== (h & d)) e[g] = vc(h, b);
          } else k <= b && (a.expiredLanes |= h);
          f &= ~h;
        }
      }
      function xc(a) {
        a = a.pendingLanes & -1073741825;
        return 0 !== a ? a : a & 1073741824 ? 1073741824 : 0;
      }
      function yc() {
        var a = rc;
        rc <<= 1;
        0 === (rc & 4194240) && (rc = 64);
        return a;
      }
      function zc(a) {
        for (var b = [], c = 0; 31 > c; c++) b.push(a);
        return b;
      }
      function Ac(a, b, c) {
        a.pendingLanes |= b;
        536870912 !== b && (a.suspendedLanes = 0, a.pingedLanes = 0);
        a = a.eventTimes;
        b = 31 - oc(b);
        a[b] = c;
      }
      function Bc(a, b) {
        var c = a.pendingLanes & ~b;
        a.pendingLanes = b;
        a.suspendedLanes = 0;
        a.pingedLanes = 0;
        a.expiredLanes &= b;
        a.mutableReadLanes &= b;
        a.entangledLanes &= b;
        b = a.entanglements;
        var d = a.eventTimes;
        for (a = a.expirationTimes; 0 < c; ) {
          var e = 31 - oc(c), f = 1 << e;
          b[e] = 0;
          d[e] = -1;
          a[e] = -1;
          c &= ~f;
        }
      }
      function Cc(a, b) {
        var c = a.entangledLanes |= b;
        for (a = a.entanglements; c; ) {
          var d = 31 - oc(c), e = 1 << d;
          e & b | a[d] & b && (a[d] |= b);
          c &= ~e;
        }
      }
      var C = 0;
      function Dc(a) {
        a &= -a;
        return 1 < a ? 4 < a ? 0 !== (a & 268435455) ? 16 : 536870912 : 4 : 1;
      }
      var Ec;
      var Fc;
      var Gc;
      var Hc;
      var Ic;
      var Jc = false;
      var Kc = [];
      var Lc = null;
      var Mc = null;
      var Nc = null;
      var Oc = /* @__PURE__ */ new Map();
      var Pc = /* @__PURE__ */ new Map();
      var Qc = [];
      var Rc = "mousedown mouseup touchcancel touchend touchstart auxclick dblclick pointercancel pointerdown pointerup dragend dragstart drop compositionend compositionstart keydown keypress keyup input textInput copy cut paste click change contextmenu reset submit".split(" ");
      function Sc(a, b) {
        switch (a) {
          case "focusin":
          case "focusout":
            Lc = null;
            break;
          case "dragenter":
          case "dragleave":
            Mc = null;
            break;
          case "mouseover":
          case "mouseout":
            Nc = null;
            break;
          case "pointerover":
          case "pointerout":
            Oc.delete(b.pointerId);
            break;
          case "gotpointercapture":
          case "lostpointercapture":
            Pc.delete(b.pointerId);
        }
      }
      function Tc(a, b, c, d, e, f) {
        if (null === a || a.nativeEvent !== f) return a = { blockedOn: b, domEventName: c, eventSystemFlags: d, nativeEvent: f, targetContainers: [e] }, null !== b && (b = Cb(b), null !== b && Fc(b)), a;
        a.eventSystemFlags |= d;
        b = a.targetContainers;
        null !== e && -1 === b.indexOf(e) && b.push(e);
        return a;
      }
      function Uc(a, b, c, d, e) {
        switch (b) {
          case "focusin":
            return Lc = Tc(Lc, a, b, c, d, e), true;
          case "dragenter":
            return Mc = Tc(Mc, a, b, c, d, e), true;
          case "mouseover":
            return Nc = Tc(Nc, a, b, c, d, e), true;
          case "pointerover":
            var f = e.pointerId;
            Oc.set(f, Tc(Oc.get(f) || null, a, b, c, d, e));
            return true;
          case "gotpointercapture":
            return f = e.pointerId, Pc.set(f, Tc(Pc.get(f) || null, a, b, c, d, e)), true;
        }
        return false;
      }
      function Vc(a) {
        var b = Wc(a.target);
        if (null !== b) {
          var c = Vb(b);
          if (null !== c) {
            if (b = c.tag, 13 === b) {
              if (b = Wb(c), null !== b) {
                a.blockedOn = b;
                Ic(a.priority, function() {
                  Gc(c);
                });
                return;
              }
            } else if (3 === b && c.stateNode.current.memoizedState.isDehydrated) {
              a.blockedOn = 3 === c.tag ? c.stateNode.containerInfo : null;
              return;
            }
          }
        }
        a.blockedOn = null;
      }
      function Xc(a) {
        if (null !== a.blockedOn) return false;
        for (var b = a.targetContainers; 0 < b.length; ) {
          var c = Yc(a.domEventName, a.eventSystemFlags, b[0], a.nativeEvent);
          if (null === c) {
            c = a.nativeEvent;
            var d = new c.constructor(c.type, c);
            wb = d;
            c.target.dispatchEvent(d);
            wb = null;
          } else return b = Cb(c), null !== b && Fc(b), a.blockedOn = c, false;
          b.shift();
        }
        return true;
      }
      function Zc(a, b, c) {
        Xc(a) && c.delete(b);
      }
      function $c() {
        Jc = false;
        null !== Lc && Xc(Lc) && (Lc = null);
        null !== Mc && Xc(Mc) && (Mc = null);
        null !== Nc && Xc(Nc) && (Nc = null);
        Oc.forEach(Zc);
        Pc.forEach(Zc);
      }
      function ad(a, b) {
        a.blockedOn === b && (a.blockedOn = null, Jc || (Jc = true, ca.unstable_scheduleCallback(ca.unstable_NormalPriority, $c)));
      }
      function bd(a) {
        function b(b2) {
          return ad(b2, a);
        }
        if (0 < Kc.length) {
          ad(Kc[0], a);
          for (var c = 1; c < Kc.length; c++) {
            var d = Kc[c];
            d.blockedOn === a && (d.blockedOn = null);
          }
        }
        null !== Lc && ad(Lc, a);
        null !== Mc && ad(Mc, a);
        null !== Nc && ad(Nc, a);
        Oc.forEach(b);
        Pc.forEach(b);
        for (c = 0; c < Qc.length; c++) d = Qc[c], d.blockedOn === a && (d.blockedOn = null);
        for (; 0 < Qc.length && (c = Qc[0], null === c.blockedOn); ) Vc(c), null === c.blockedOn && Qc.shift();
      }
      var cd = ua.ReactCurrentBatchConfig;
      var dd = true;
      function ed(a, b, c, d) {
        var e = C, f = cd.transition;
        cd.transition = null;
        try {
          C = 1, fd(a, b, c, d);
        } finally {
          C = e, cd.transition = f;
        }
      }
      function gd(a, b, c, d) {
        var e = C, f = cd.transition;
        cd.transition = null;
        try {
          C = 4, fd(a, b, c, d);
        } finally {
          C = e, cd.transition = f;
        }
      }
      function fd(a, b, c, d) {
        if (dd) {
          var e = Yc(a, b, c, d);
          if (null === e) hd(a, b, d, id, c), Sc(a, d);
          else if (Uc(e, a, b, c, d)) d.stopPropagation();
          else if (Sc(a, d), b & 4 && -1 < Rc.indexOf(a)) {
            for (; null !== e; ) {
              var f = Cb(e);
              null !== f && Ec(f);
              f = Yc(a, b, c, d);
              null === f && hd(a, b, d, id, c);
              if (f === e) break;
              e = f;
            }
            null !== e && d.stopPropagation();
          } else hd(a, b, d, null, c);
        }
      }
      var id = null;
      function Yc(a, b, c, d) {
        id = null;
        a = xb(d);
        a = Wc(a);
        if (null !== a) if (b = Vb(a), null === b) a = null;
        else if (c = b.tag, 13 === c) {
          a = Wb(b);
          if (null !== a) return a;
          a = null;
        } else if (3 === c) {
          if (b.stateNode.current.memoizedState.isDehydrated) return 3 === b.tag ? b.stateNode.containerInfo : null;
          a = null;
        } else b !== a && (a = null);
        id = a;
        return null;
      }
      function jd(a) {
        switch (a) {
          case "cancel":
          case "click":
          case "close":
          case "contextmenu":
          case "copy":
          case "cut":
          case "auxclick":
          case "dblclick":
          case "dragend":
          case "dragstart":
          case "drop":
          case "focusin":
          case "focusout":
          case "input":
          case "invalid":
          case "keydown":
          case "keypress":
          case "keyup":
          case "mousedown":
          case "mouseup":
          case "paste":
          case "pause":
          case "play":
          case "pointercancel":
          case "pointerdown":
          case "pointerup":
          case "ratechange":
          case "reset":
          case "resize":
          case "seeked":
          case "submit":
          case "touchcancel":
          case "touchend":
          case "touchstart":
          case "volumechange":
          case "change":
          case "selectionchange":
          case "textInput":
          case "compositionstart":
          case "compositionend":
          case "compositionupdate":
          case "beforeblur":
          case "afterblur":
          case "beforeinput":
          case "blur":
          case "fullscreenchange":
          case "focus":
          case "hashchange":
          case "popstate":
          case "select":
          case "selectstart":
            return 1;
          case "drag":
          case "dragenter":
          case "dragexit":
          case "dragleave":
          case "dragover":
          case "mousemove":
          case "mouseout":
          case "mouseover":
          case "pointermove":
          case "pointerout":
          case "pointerover":
          case "scroll":
          case "toggle":
          case "touchmove":
          case "wheel":
          case "mouseenter":
          case "mouseleave":
          case "pointerenter":
          case "pointerleave":
            return 4;
          case "message":
            switch (ec()) {
              case fc:
                return 1;
              case gc:
                return 4;
              case hc:
              case ic:
                return 16;
              case jc:
                return 536870912;
              default:
                return 16;
            }
          default:
            return 16;
        }
      }
      var kd = null;
      var ld = null;
      var md = null;
      function nd() {
        if (md) return md;
        var a, b = ld, c = b.length, d, e = "value" in kd ? kd.value : kd.textContent, f = e.length;
        for (a = 0; a < c && b[a] === e[a]; a++) ;
        var g = c - a;
        for (d = 1; d <= g && b[c - d] === e[f - d]; d++) ;
        return md = e.slice(a, 1 < d ? 1 - d : void 0);
      }
      function od(a) {
        var b = a.keyCode;
        "charCode" in a ? (a = a.charCode, 0 === a && 13 === b && (a = 13)) : a = b;
        10 === a && (a = 13);
        return 32 <= a || 13 === a ? a : 0;
      }
      function pd() {
        return true;
      }
      function qd() {
        return false;
      }
      function rd(a) {
        function b(b2, d, e, f, g) {
          this._reactName = b2;
          this._targetInst = e;
          this.type = d;
          this.nativeEvent = f;
          this.target = g;
          this.currentTarget = null;
          for (var c in a) a.hasOwnProperty(c) && (b2 = a[c], this[c] = b2 ? b2(f) : f[c]);
          this.isDefaultPrevented = (null != f.defaultPrevented ? f.defaultPrevented : false === f.returnValue) ? pd : qd;
          this.isPropagationStopped = qd;
          return this;
        }
        A(b.prototype, { preventDefault: function() {
          this.defaultPrevented = true;
          var a2 = this.nativeEvent;
          a2 && (a2.preventDefault ? a2.preventDefault() : "unknown" !== typeof a2.returnValue && (a2.returnValue = false), this.isDefaultPrevented = pd);
        }, stopPropagation: function() {
          var a2 = this.nativeEvent;
          a2 && (a2.stopPropagation ? a2.stopPropagation() : "unknown" !== typeof a2.cancelBubble && (a2.cancelBubble = true), this.isPropagationStopped = pd);
        }, persist: function() {
        }, isPersistent: pd });
        return b;
      }
      var sd = { eventPhase: 0, bubbles: 0, cancelable: 0, timeStamp: function(a) {
        return a.timeStamp || Date.now();
      }, defaultPrevented: 0, isTrusted: 0 };
      var td = rd(sd);
      var ud = A({}, sd, { view: 0, detail: 0 });
      var vd = rd(ud);
      var wd;
      var xd;
      var yd;
      var Ad = A({}, ud, { screenX: 0, screenY: 0, clientX: 0, clientY: 0, pageX: 0, pageY: 0, ctrlKey: 0, shiftKey: 0, altKey: 0, metaKey: 0, getModifierState: zd, button: 0, buttons: 0, relatedTarget: function(a) {
        return void 0 === a.relatedTarget ? a.fromElement === a.srcElement ? a.toElement : a.fromElement : a.relatedTarget;
      }, movementX: function(a) {
        if ("movementX" in a) return a.movementX;
        a !== yd && (yd && "mousemove" === a.type ? (wd = a.screenX - yd.screenX, xd = a.screenY - yd.screenY) : xd = wd = 0, yd = a);
        return wd;
      }, movementY: function(a) {
        return "movementY" in a ? a.movementY : xd;
      } });
      var Bd = rd(Ad);
      var Cd = A({}, Ad, { dataTransfer: 0 });
      var Dd = rd(Cd);
      var Ed = A({}, ud, { relatedTarget: 0 });
      var Fd = rd(Ed);
      var Gd = A({}, sd, { animationName: 0, elapsedTime: 0, pseudoElement: 0 });
      var Hd = rd(Gd);
      var Id = A({}, sd, { clipboardData: function(a) {
        return "clipboardData" in a ? a.clipboardData : window.clipboardData;
      } });
      var Jd = rd(Id);
      var Kd = A({}, sd, { data: 0 });
      var Ld = rd(Kd);
      var Md = {
        Esc: "Escape",
        Spacebar: " ",
        Left: "ArrowLeft",
        Up: "ArrowUp",
        Right: "ArrowRight",
        Down: "ArrowDown",
        Del: "Delete",
        Win: "OS",
        Menu: "ContextMenu",
        Apps: "ContextMenu",
        Scroll: "ScrollLock",
        MozPrintableKey: "Unidentified"
      };
      var Nd = {
        8: "Backspace",
        9: "Tab",
        12: "Clear",
        13: "Enter",
        16: "Shift",
        17: "Control",
        18: "Alt",
        19: "Pause",
        20: "CapsLock",
        27: "Escape",
        32: " ",
        33: "PageUp",
        34: "PageDown",
        35: "End",
        36: "Home",
        37: "ArrowLeft",
        38: "ArrowUp",
        39: "ArrowRight",
        40: "ArrowDown",
        45: "Insert",
        46: "Delete",
        112: "F1",
        113: "F2",
        114: "F3",
        115: "F4",
        116: "F5",
        117: "F6",
        118: "F7",
        119: "F8",
        120: "F9",
        121: "F10",
        122: "F11",
        123: "F12",
        144: "NumLock",
        145: "ScrollLock",
        224: "Meta"
      };
      var Od = { Alt: "altKey", Control: "ctrlKey", Meta: "metaKey", Shift: "shiftKey" };
      function Pd(a) {
        var b = this.nativeEvent;
        return b.getModifierState ? b.getModifierState(a) : (a = Od[a]) ? !!b[a] : false;
      }
      function zd() {
        return Pd;
      }
      var Qd = A({}, ud, { key: function(a) {
        if (a.key) {
          var b = Md[a.key] || a.key;
          if ("Unidentified" !== b) return b;
        }
        return "keypress" === a.type ? (a = od(a), 13 === a ? "Enter" : String.fromCharCode(a)) : "keydown" === a.type || "keyup" === a.type ? Nd[a.keyCode] || "Unidentified" : "";
      }, code: 0, location: 0, ctrlKey: 0, shiftKey: 0, altKey: 0, metaKey: 0, repeat: 0, locale: 0, getModifierState: zd, charCode: function(a) {
        return "keypress" === a.type ? od(a) : 0;
      }, keyCode: function(a) {
        return "keydown" === a.type || "keyup" === a.type ? a.keyCode : 0;
      }, which: function(a) {
        return "keypress" === a.type ? od(a) : "keydown" === a.type || "keyup" === a.type ? a.keyCode : 0;
      } });
      var Rd = rd(Qd);
      var Sd = A({}, Ad, { pointerId: 0, width: 0, height: 0, pressure: 0, tangentialPressure: 0, tiltX: 0, tiltY: 0, twist: 0, pointerType: 0, isPrimary: 0 });
      var Td = rd(Sd);
      var Ud = A({}, ud, { touches: 0, targetTouches: 0, changedTouches: 0, altKey: 0, metaKey: 0, ctrlKey: 0, shiftKey: 0, getModifierState: zd });
      var Vd = rd(Ud);
      var Wd = A({}, sd, { propertyName: 0, elapsedTime: 0, pseudoElement: 0 });
      var Xd = rd(Wd);
      var Yd = A({}, Ad, {
        deltaX: function(a) {
          return "deltaX" in a ? a.deltaX : "wheelDeltaX" in a ? -a.wheelDeltaX : 0;
        },
        deltaY: function(a) {
          return "deltaY" in a ? a.deltaY : "wheelDeltaY" in a ? -a.wheelDeltaY : "wheelDelta" in a ? -a.wheelDelta : 0;
        },
        deltaZ: 0,
        deltaMode: 0
      });
      var Zd = rd(Yd);
      var $d = [9, 13, 27, 32];
      var ae = ia && "CompositionEvent" in window;
      var be = null;
      ia && "documentMode" in document && (be = document.documentMode);
      var ce = ia && "TextEvent" in window && !be;
      var de = ia && (!ae || be && 8 < be && 11 >= be);
      var ee = String.fromCharCode(32);
      var fe = false;
      function ge(a, b) {
        switch (a) {
          case "keyup":
            return -1 !== $d.indexOf(b.keyCode);
          case "keydown":
            return 229 !== b.keyCode;
          case "keypress":
          case "mousedown":
          case "focusout":
            return true;
          default:
            return false;
        }
      }
      function he(a) {
        a = a.detail;
        return "object" === typeof a && "data" in a ? a.data : null;
      }
      var ie = false;
      function je(a, b) {
        switch (a) {
          case "compositionend":
            return he(b);
          case "keypress":
            if (32 !== b.which) return null;
            fe = true;
            return ee;
          case "textInput":
            return a = b.data, a === ee && fe ? null : a;
          default:
            return null;
        }
      }
      function ke(a, b) {
        if (ie) return "compositionend" === a || !ae && ge(a, b) ? (a = nd(), md = ld = kd = null, ie = false, a) : null;
        switch (a) {
          case "paste":
            return null;
          case "keypress":
            if (!(b.ctrlKey || b.altKey || b.metaKey) || b.ctrlKey && b.altKey) {
              if (b.char && 1 < b.char.length) return b.char;
              if (b.which) return String.fromCharCode(b.which);
            }
            return null;
          case "compositionend":
            return de && "ko" !== b.locale ? null : b.data;
          default:
            return null;
        }
      }
      var le = { color: true, date: true, datetime: true, "datetime-local": true, email: true, month: true, number: true, password: true, range: true, search: true, tel: true, text: true, time: true, url: true, week: true };
      function me(a) {
        var b = a && a.nodeName && a.nodeName.toLowerCase();
        return "input" === b ? !!le[a.type] : "textarea" === b ? true : false;
      }
      function ne(a, b, c, d) {
        Eb(d);
        b = oe(b, "onChange");
        0 < b.length && (c = new td("onChange", "change", null, c, d), a.push({ event: c, listeners: b }));
      }
      var pe = null;
      var qe = null;
      function re(a) {
        se(a, 0);
      }
      function te(a) {
        var b = ue(a);
        if (Wa(b)) return a;
      }
      function ve(a, b) {
        if ("change" === a) return b;
      }
      var we = false;
      if (ia) {
        if (ia) {
          ye = "oninput" in document;
          if (!ye) {
            ze = document.createElement("div");
            ze.setAttribute("oninput", "return;");
            ye = "function" === typeof ze.oninput;
          }
          xe = ye;
        } else xe = false;
        we = xe && (!document.documentMode || 9 < document.documentMode);
      }
      var xe;
      var ye;
      var ze;
      function Ae() {
        pe && (pe.detachEvent("onpropertychange", Be), qe = pe = null);
      }
      function Be(a) {
        if ("value" === a.propertyName && te(qe)) {
          var b = [];
          ne(b, qe, a, xb(a));
          Jb(re, b);
        }
      }
      function Ce(a, b, c) {
        "focusin" === a ? (Ae(), pe = b, qe = c, pe.attachEvent("onpropertychange", Be)) : "focusout" === a && Ae();
      }
      function De(a) {
        if ("selectionchange" === a || "keyup" === a || "keydown" === a) return te(qe);
      }
      function Ee(a, b) {
        if ("click" === a) return te(b);
      }
      function Fe(a, b) {
        if ("input" === a || "change" === a) return te(b);
      }
      function Ge(a, b) {
        return a === b && (0 !== a || 1 / a === 1 / b) || a !== a && b !== b;
      }
      var He = "function" === typeof Object.is ? Object.is : Ge;
      function Ie(a, b) {
        if (He(a, b)) return true;
        if ("object" !== typeof a || null === a || "object" !== typeof b || null === b) return false;
        var c = Object.keys(a), d = Object.keys(b);
        if (c.length !== d.length) return false;
        for (d = 0; d < c.length; d++) {
          var e = c[d];
          if (!ja.call(b, e) || !He(a[e], b[e])) return false;
        }
        return true;
      }
      function Je(a) {
        for (; a && a.firstChild; ) a = a.firstChild;
        return a;
      }
      function Ke(a, b) {
        var c = Je(a);
        a = 0;
        for (var d; c; ) {
          if (3 === c.nodeType) {
            d = a + c.textContent.length;
            if (a <= b && d >= b) return { node: c, offset: b - a };
            a = d;
          }
          a: {
            for (; c; ) {
              if (c.nextSibling) {
                c = c.nextSibling;
                break a;
              }
              c = c.parentNode;
            }
            c = void 0;
          }
          c = Je(c);
        }
      }
      function Le(a, b) {
        return a && b ? a === b ? true : a && 3 === a.nodeType ? false : b && 3 === b.nodeType ? Le(a, b.parentNode) : "contains" in a ? a.contains(b) : a.compareDocumentPosition ? !!(a.compareDocumentPosition(b) & 16) : false : false;
      }
      function Me() {
        for (var a = window, b = Xa(); b instanceof a.HTMLIFrameElement; ) {
          try {
            var c = "string" === typeof b.contentWindow.location.href;
          } catch (d) {
            c = false;
          }
          if (c) a = b.contentWindow;
          else break;
          b = Xa(a.document);
        }
        return b;
      }
      function Ne(a) {
        var b = a && a.nodeName && a.nodeName.toLowerCase();
        return b && ("input" === b && ("text" === a.type || "search" === a.type || "tel" === a.type || "url" === a.type || "password" === a.type) || "textarea" === b || "true" === a.contentEditable);
      }
      function Oe(a) {
        var b = Me(), c = a.focusedElem, d = a.selectionRange;
        if (b !== c && c && c.ownerDocument && Le(c.ownerDocument.documentElement, c)) {
          if (null !== d && Ne(c)) {
            if (b = d.start, a = d.end, void 0 === a && (a = b), "selectionStart" in c) c.selectionStart = b, c.selectionEnd = Math.min(a, c.value.length);
            else if (a = (b = c.ownerDocument || document) && b.defaultView || window, a.getSelection) {
              a = a.getSelection();
              var e = c.textContent.length, f = Math.min(d.start, e);
              d = void 0 === d.end ? f : Math.min(d.end, e);
              !a.extend && f > d && (e = d, d = f, f = e);
              e = Ke(c, f);
              var g = Ke(
                c,
                d
              );
              e && g && (1 !== a.rangeCount || a.anchorNode !== e.node || a.anchorOffset !== e.offset || a.focusNode !== g.node || a.focusOffset !== g.offset) && (b = b.createRange(), b.setStart(e.node, e.offset), a.removeAllRanges(), f > d ? (a.addRange(b), a.extend(g.node, g.offset)) : (b.setEnd(g.node, g.offset), a.addRange(b)));
            }
          }
          b = [];
          for (a = c; a = a.parentNode; ) 1 === a.nodeType && b.push({ element: a, left: a.scrollLeft, top: a.scrollTop });
          "function" === typeof c.focus && c.focus();
          for (c = 0; c < b.length; c++) a = b[c], a.element.scrollLeft = a.left, a.element.scrollTop = a.top;
        }
      }
      var Pe = ia && "documentMode" in document && 11 >= document.documentMode;
      var Qe = null;
      var Re = null;
      var Se = null;
      var Te = false;
      function Ue(a, b, c) {
        var d = c.window === c ? c.document : 9 === c.nodeType ? c : c.ownerDocument;
        Te || null == Qe || Qe !== Xa(d) || (d = Qe, "selectionStart" in d && Ne(d) ? d = { start: d.selectionStart, end: d.selectionEnd } : (d = (d.ownerDocument && d.ownerDocument.defaultView || window).getSelection(), d = { anchorNode: d.anchorNode, anchorOffset: d.anchorOffset, focusNode: d.focusNode, focusOffset: d.focusOffset }), Se && Ie(Se, d) || (Se = d, d = oe(Re, "onSelect"), 0 < d.length && (b = new td("onSelect", "select", null, b, c), a.push({ event: b, listeners: d }), b.target = Qe)));
      }
      function Ve(a, b) {
        var c = {};
        c[a.toLowerCase()] = b.toLowerCase();
        c["Webkit" + a] = "webkit" + b;
        c["Moz" + a] = "moz" + b;
        return c;
      }
      var We = { animationend: Ve("Animation", "AnimationEnd"), animationiteration: Ve("Animation", "AnimationIteration"), animationstart: Ve("Animation", "AnimationStart"), transitionend: Ve("Transition", "TransitionEnd") };
      var Xe = {};
      var Ye = {};
      ia && (Ye = document.createElement("div").style, "AnimationEvent" in window || (delete We.animationend.animation, delete We.animationiteration.animation, delete We.animationstart.animation), "TransitionEvent" in window || delete We.transitionend.transition);
      function Ze(a) {
        if (Xe[a]) return Xe[a];
        if (!We[a]) return a;
        var b = We[a], c;
        for (c in b) if (b.hasOwnProperty(c) && c in Ye) return Xe[a] = b[c];
        return a;
      }
      var $e = Ze("animationend");
      var af = Ze("animationiteration");
      var bf = Ze("animationstart");
      var cf = Ze("transitionend");
      var df = /* @__PURE__ */ new Map();
      var ef = "abort auxClick cancel canPlay canPlayThrough click close contextMenu copy cut drag dragEnd dragEnter dragExit dragLeave dragOver dragStart drop durationChange emptied encrypted ended error gotPointerCapture input invalid keyDown keyPress keyUp load loadedData loadedMetadata loadStart lostPointerCapture mouseDown mouseMove mouseOut mouseOver mouseUp paste pause play playing pointerCancel pointerDown pointerMove pointerOut pointerOver pointerUp progress rateChange reset resize seeked seeking stalled submit suspend timeUpdate touchCancel touchEnd touchStart volumeChange scroll toggle touchMove waiting wheel".split(" ");
      function ff(a, b) {
        df.set(a, b);
        fa(b, [a]);
      }
      for (gf = 0; gf < ef.length; gf++) {
        hf = ef[gf], jf = hf.toLowerCase(), kf = hf[0].toUpperCase() + hf.slice(1);
        ff(jf, "on" + kf);
      }
      var hf;
      var jf;
      var kf;
      var gf;
      ff($e, "onAnimationEnd");
      ff(af, "onAnimationIteration");
      ff(bf, "onAnimationStart");
      ff("dblclick", "onDoubleClick");
      ff("focusin", "onFocus");
      ff("focusout", "onBlur");
      ff(cf, "onTransitionEnd");
      ha("onMouseEnter", ["mouseout", "mouseover"]);
      ha("onMouseLeave", ["mouseout", "mouseover"]);
      ha("onPointerEnter", ["pointerout", "pointerover"]);
      ha("onPointerLeave", ["pointerout", "pointerover"]);
      fa("onChange", "change click focusin focusout input keydown keyup selectionchange".split(" "));
      fa("onSelect", "focusout contextmenu dragend focusin keydown keyup mousedown mouseup selectionchange".split(" "));
      fa("onBeforeInput", ["compositionend", "keypress", "textInput", "paste"]);
      fa("onCompositionEnd", "compositionend focusout keydown keypress keyup mousedown".split(" "));
      fa("onCompositionStart", "compositionstart focusout keydown keypress keyup mousedown".split(" "));
      fa("onCompositionUpdate", "compositionupdate focusout keydown keypress keyup mousedown".split(" "));
      var lf = "abort canplay canplaythrough durationchange emptied encrypted ended error loadeddata loadedmetadata loadstart pause play playing progress ratechange resize seeked seeking stalled suspend timeupdate volumechange waiting".split(" ");
      var mf = new Set("cancel close invalid load scroll toggle".split(" ").concat(lf));
      function nf(a, b, c) {
        var d = a.type || "unknown-event";
        a.currentTarget = c;
        Ub(d, b, void 0, a);
        a.currentTarget = null;
      }
      function se(a, b) {
        b = 0 !== (b & 4);
        for (var c = 0; c < a.length; c++) {
          var d = a[c], e = d.event;
          d = d.listeners;
          a: {
            var f = void 0;
            if (b) for (var g = d.length - 1; 0 <= g; g--) {
              var h = d[g], k = h.instance, l = h.currentTarget;
              h = h.listener;
              if (k !== f && e.isPropagationStopped()) break a;
              nf(e, h, l);
              f = k;
            }
            else for (g = 0; g < d.length; g++) {
              h = d[g];
              k = h.instance;
              l = h.currentTarget;
              h = h.listener;
              if (k !== f && e.isPropagationStopped()) break a;
              nf(e, h, l);
              f = k;
            }
          }
        }
        if (Qb) throw a = Rb, Qb = false, Rb = null, a;
      }
      function D(a, b) {
        var c = b[of];
        void 0 === c && (c = b[of] = /* @__PURE__ */ new Set());
        var d = a + "__bubble";
        c.has(d) || (pf(b, a, 2, false), c.add(d));
      }
      function qf(a, b, c) {
        var d = 0;
        b && (d |= 4);
        pf(c, a, d, b);
      }
      var rf = "_reactListening" + Math.random().toString(36).slice(2);
      function sf(a) {
        if (!a[rf]) {
          a[rf] = true;
          da.forEach(function(b2) {
            "selectionchange" !== b2 && (mf.has(b2) || qf(b2, false, a), qf(b2, true, a));
          });
          var b = 9 === a.nodeType ? a : a.ownerDocument;
          null === b || b[rf] || (b[rf] = true, qf("selectionchange", false, b));
        }
      }
      function pf(a, b, c, d) {
        switch (jd(b)) {
          case 1:
            var e = ed;
            break;
          case 4:
            e = gd;
            break;
          default:
            e = fd;
        }
        c = e.bind(null, b, c, a);
        e = void 0;
        !Lb || "touchstart" !== b && "touchmove" !== b && "wheel" !== b || (e = true);
        d ? void 0 !== e ? a.addEventListener(b, c, { capture: true, passive: e }) : a.addEventListener(b, c, true) : void 0 !== e ? a.addEventListener(b, c, { passive: e }) : a.addEventListener(b, c, false);
      }
      function hd(a, b, c, d, e) {
        var f = d;
        if (0 === (b & 1) && 0 === (b & 2) && null !== d) a: for (; ; ) {
          if (null === d) return;
          var g = d.tag;
          if (3 === g || 4 === g) {
            var h = d.stateNode.containerInfo;
            if (h === e || 8 === h.nodeType && h.parentNode === e) break;
            if (4 === g) for (g = d.return; null !== g; ) {
              var k = g.tag;
              if (3 === k || 4 === k) {
                if (k = g.stateNode.containerInfo, k === e || 8 === k.nodeType && k.parentNode === e) return;
              }
              g = g.return;
            }
            for (; null !== h; ) {
              g = Wc(h);
              if (null === g) return;
              k = g.tag;
              if (5 === k || 6 === k) {
                d = f = g;
                continue a;
              }
              h = h.parentNode;
            }
          }
          d = d.return;
        }
        Jb(function() {
          var d2 = f, e2 = xb(c), g2 = [];
          a: {
            var h2 = df.get(a);
            if (void 0 !== h2) {
              var k2 = td, n = a;
              switch (a) {
                case "keypress":
                  if (0 === od(c)) break a;
                case "keydown":
                case "keyup":
                  k2 = Rd;
                  break;
                case "focusin":
                  n = "focus";
                  k2 = Fd;
                  break;
                case "focusout":
                  n = "blur";
                  k2 = Fd;
                  break;
                case "beforeblur":
                case "afterblur":
                  k2 = Fd;
                  break;
                case "click":
                  if (2 === c.button) break a;
                case "auxclick":
                case "dblclick":
                case "mousedown":
                case "mousemove":
                case "mouseup":
                case "mouseout":
                case "mouseover":
                case "contextmenu":
                  k2 = Bd;
                  break;
                case "drag":
                case "dragend":
                case "dragenter":
                case "dragexit":
                case "dragleave":
                case "dragover":
                case "dragstart":
                case "drop":
                  k2 = Dd;
                  break;
                case "touchcancel":
                case "touchend":
                case "touchmove":
                case "touchstart":
                  k2 = Vd;
                  break;
                case $e:
                case af:
                case bf:
                  k2 = Hd;
                  break;
                case cf:
                  k2 = Xd;
                  break;
                case "scroll":
                  k2 = vd;
                  break;
                case "wheel":
                  k2 = Zd;
                  break;
                case "copy":
                case "cut":
                case "paste":
                  k2 = Jd;
                  break;
                case "gotpointercapture":
                case "lostpointercapture":
                case "pointercancel":
                case "pointerdown":
                case "pointermove":
                case "pointerout":
                case "pointerover":
                case "pointerup":
                  k2 = Td;
              }
              var t = 0 !== (b & 4), J = !t && "scroll" === a, x = t ? null !== h2 ? h2 + "Capture" : null : h2;
              t = [];
              for (var w = d2, u; null !== w; ) {
                u = w;
                var F = u.stateNode;
                5 === u.tag && null !== F && (u = F, null !== x && (F = Kb(w, x), null != F && t.push(tf(w, F, u))));
                if (J) break;
                w = w.return;
              }
              0 < t.length && (h2 = new k2(h2, n, null, c, e2), g2.push({ event: h2, listeners: t }));
            }
          }
          if (0 === (b & 7)) {
            a: {
              h2 = "mouseover" === a || "pointerover" === a;
              k2 = "mouseout" === a || "pointerout" === a;
              if (h2 && c !== wb && (n = c.relatedTarget || c.fromElement) && (Wc(n) || n[uf])) break a;
              if (k2 || h2) {
                h2 = e2.window === e2 ? e2 : (h2 = e2.ownerDocument) ? h2.defaultView || h2.parentWindow : window;
                if (k2) {
                  if (n = c.relatedTarget || c.toElement, k2 = d2, n = n ? Wc(n) : null, null !== n && (J = Vb(n), n !== J || 5 !== n.tag && 6 !== n.tag)) n = null;
                } else k2 = null, n = d2;
                if (k2 !== n) {
                  t = Bd;
                  F = "onMouseLeave";
                  x = "onMouseEnter";
                  w = "mouse";
                  if ("pointerout" === a || "pointerover" === a) t = Td, F = "onPointerLeave", x = "onPointerEnter", w = "pointer";
                  J = null == k2 ? h2 : ue(k2);
                  u = null == n ? h2 : ue(n);
                  h2 = new t(F, w + "leave", k2, c, e2);
                  h2.target = J;
                  h2.relatedTarget = u;
                  F = null;
                  Wc(e2) === d2 && (t = new t(x, w + "enter", n, c, e2), t.target = u, t.relatedTarget = J, F = t);
                  J = F;
                  if (k2 && n) b: {
                    t = k2;
                    x = n;
                    w = 0;
                    for (u = t; u; u = vf(u)) w++;
                    u = 0;
                    for (F = x; F; F = vf(F)) u++;
                    for (; 0 < w - u; ) t = vf(t), w--;
                    for (; 0 < u - w; ) x = vf(x), u--;
                    for (; w--; ) {
                      if (t === x || null !== x && t === x.alternate) break b;
                      t = vf(t);
                      x = vf(x);
                    }
                    t = null;
                  }
                  else t = null;
                  null !== k2 && wf(g2, h2, k2, t, false);
                  null !== n && null !== J && wf(g2, J, n, t, true);
                }
              }
            }
            a: {
              h2 = d2 ? ue(d2) : window;
              k2 = h2.nodeName && h2.nodeName.toLowerCase();
              if ("select" === k2 || "input" === k2 && "file" === h2.type) var na = ve;
              else if (me(h2)) if (we) na = Fe;
              else {
                na = De;
                var xa = Ce;
              }
              else (k2 = h2.nodeName) && "input" === k2.toLowerCase() && ("checkbox" === h2.type || "radio" === h2.type) && (na = Ee);
              if (na && (na = na(a, d2))) {
                ne(g2, na, c, e2);
                break a;
              }
              xa && xa(a, h2, d2);
              "focusout" === a && (xa = h2._wrapperState) && xa.controlled && "number" === h2.type && cb(h2, "number", h2.value);
            }
            xa = d2 ? ue(d2) : window;
            switch (a) {
              case "focusin":
                if (me(xa) || "true" === xa.contentEditable) Qe = xa, Re = d2, Se = null;
                break;
              case "focusout":
                Se = Re = Qe = null;
                break;
              case "mousedown":
                Te = true;
                break;
              case "contextmenu":
              case "mouseup":
              case "dragend":
                Te = false;
                Ue(g2, c, e2);
                break;
              case "selectionchange":
                if (Pe) break;
              case "keydown":
              case "keyup":
                Ue(g2, c, e2);
            }
            var $a;
            if (ae) b: {
              switch (a) {
                case "compositionstart":
                  var ba = "onCompositionStart";
                  break b;
                case "compositionend":
                  ba = "onCompositionEnd";
                  break b;
                case "compositionupdate":
                  ba = "onCompositionUpdate";
                  break b;
              }
              ba = void 0;
            }
            else ie ? ge(a, c) && (ba = "onCompositionEnd") : "keydown" === a && 229 === c.keyCode && (ba = "onCompositionStart");
            ba && (de && "ko" !== c.locale && (ie || "onCompositionStart" !== ba ? "onCompositionEnd" === ba && ie && ($a = nd()) : (kd = e2, ld = "value" in kd ? kd.value : kd.textContent, ie = true)), xa = oe(d2, ba), 0 < xa.length && (ba = new Ld(ba, a, null, c, e2), g2.push({ event: ba, listeners: xa }), $a ? ba.data = $a : ($a = he(c), null !== $a && (ba.data = $a))));
            if ($a = ce ? je(a, c) : ke(a, c)) d2 = oe(d2, "onBeforeInput"), 0 < d2.length && (e2 = new Ld("onBeforeInput", "beforeinput", null, c, e2), g2.push({ event: e2, listeners: d2 }), e2.data = $a);
          }
          se(g2, b);
        });
      }
      function tf(a, b, c) {
        return { instance: a, listener: b, currentTarget: c };
      }
      function oe(a, b) {
        for (var c = b + "Capture", d = []; null !== a; ) {
          var e = a, f = e.stateNode;
          5 === e.tag && null !== f && (e = f, f = Kb(a, c), null != f && d.unshift(tf(a, f, e)), f = Kb(a, b), null != f && d.push(tf(a, f, e)));
          a = a.return;
        }
        return d;
      }
      function vf(a) {
        if (null === a) return null;
        do
          a = a.return;
        while (a && 5 !== a.tag);
        return a ? a : null;
      }
      function wf(a, b, c, d, e) {
        for (var f = b._reactName, g = []; null !== c && c !== d; ) {
          var h = c, k = h.alternate, l = h.stateNode;
          if (null !== k && k === d) break;
          5 === h.tag && null !== l && (h = l, e ? (k = Kb(c, f), null != k && g.unshift(tf(c, k, h))) : e || (k = Kb(c, f), null != k && g.push(tf(c, k, h))));
          c = c.return;
        }
        0 !== g.length && a.push({ event: b, listeners: g });
      }
      var xf = /\r\n?/g;
      var yf = /\u0000|\uFFFD/g;
      function zf(a) {
        return ("string" === typeof a ? a : "" + a).replace(xf, "\n").replace(yf, "");
      }
      function Af(a, b, c) {
        b = zf(b);
        if (zf(a) !== b && c) throw Error(p(425));
      }
      function Bf() {
      }
      var Cf = null;
      var Df = null;
      function Ef(a, b) {
        return "textarea" === a || "noscript" === a || "string" === typeof b.children || "number" === typeof b.children || "object" === typeof b.dangerouslySetInnerHTML && null !== b.dangerouslySetInnerHTML && null != b.dangerouslySetInnerHTML.__html;
      }
      var Ff = "function" === typeof setTimeout ? setTimeout : void 0;
      var Gf = "function" === typeof clearTimeout ? clearTimeout : void 0;
      var Hf = "function" === typeof Promise ? Promise : void 0;
      var Jf = "function" === typeof queueMicrotask ? queueMicrotask : "undefined" !== typeof Hf ? function(a) {
        return Hf.resolve(null).then(a).catch(If);
      } : Ff;
      function If(a) {
        setTimeout(function() {
          throw a;
        });
      }
      function Kf(a, b) {
        var c = b, d = 0;
        do {
          var e = c.nextSibling;
          a.removeChild(c);
          if (e && 8 === e.nodeType) if (c = e.data, "/$" === c) {
            if (0 === d) {
              a.removeChild(e);
              bd(b);
              return;
            }
            d--;
          } else "$" !== c && "$?" !== c && "$!" !== c || d++;
          c = e;
        } while (c);
        bd(b);
      }
      function Lf(a) {
        for (; null != a; a = a.nextSibling) {
          var b = a.nodeType;
          if (1 === b || 3 === b) break;
          if (8 === b) {
            b = a.data;
            if ("$" === b || "$!" === b || "$?" === b) break;
            if ("/$" === b) return null;
          }
        }
        return a;
      }
      function Mf(a) {
        a = a.previousSibling;
        for (var b = 0; a; ) {
          if (8 === a.nodeType) {
            var c = a.data;
            if ("$" === c || "$!" === c || "$?" === c) {
              if (0 === b) return a;
              b--;
            } else "/$" === c && b++;
          }
          a = a.previousSibling;
        }
        return null;
      }
      var Nf = Math.random().toString(36).slice(2);
      var Of = "__reactFiber$" + Nf;
      var Pf = "__reactProps$" + Nf;
      var uf = "__reactContainer$" + Nf;
      var of = "__reactEvents$" + Nf;
      var Qf = "__reactListeners$" + Nf;
      var Rf = "__reactHandles$" + Nf;
      function Wc(a) {
        var b = a[Of];
        if (b) return b;
        for (var c = a.parentNode; c; ) {
          if (b = c[uf] || c[Of]) {
            c = b.alternate;
            if (null !== b.child || null !== c && null !== c.child) for (a = Mf(a); null !== a; ) {
              if (c = a[Of]) return c;
              a = Mf(a);
            }
            return b;
          }
          a = c;
          c = a.parentNode;
        }
        return null;
      }
      function Cb(a) {
        a = a[Of] || a[uf];
        return !a || 5 !== a.tag && 6 !== a.tag && 13 !== a.tag && 3 !== a.tag ? null : a;
      }
      function ue(a) {
        if (5 === a.tag || 6 === a.tag) return a.stateNode;
        throw Error(p(33));
      }
      function Db(a) {
        return a[Pf] || null;
      }
      var Sf = [];
      var Tf = -1;
      function Uf(a) {
        return { current: a };
      }
      function E(a) {
        0 > Tf || (a.current = Sf[Tf], Sf[Tf] = null, Tf--);
      }
      function G(a, b) {
        Tf++;
        Sf[Tf] = a.current;
        a.current = b;
      }
      var Vf = {};
      var H = Uf(Vf);
      var Wf = Uf(false);
      var Xf = Vf;
      function Yf(a, b) {
        var c = a.type.contextTypes;
        if (!c) return Vf;
        var d = a.stateNode;
        if (d && d.__reactInternalMemoizedUnmaskedChildContext === b) return d.__reactInternalMemoizedMaskedChildContext;
        var e = {}, f;
        for (f in c) e[f] = b[f];
        d && (a = a.stateNode, a.__reactInternalMemoizedUnmaskedChildContext = b, a.__reactInternalMemoizedMaskedChildContext = e);
        return e;
      }
      function Zf(a) {
        a = a.childContextTypes;
        return null !== a && void 0 !== a;
      }
      function $f() {
        E(Wf);
        E(H);
      }
      function ag(a, b, c) {
        if (H.current !== Vf) throw Error(p(168));
        G(H, b);
        G(Wf, c);
      }
      function bg(a, b, c) {
        var d = a.stateNode;
        b = b.childContextTypes;
        if ("function" !== typeof d.getChildContext) return c;
        d = d.getChildContext();
        for (var e in d) if (!(e in b)) throw Error(p(108, Ra(a) || "Unknown", e));
        return A({}, c, d);
      }
      function cg(a) {
        a = (a = a.stateNode) && a.__reactInternalMemoizedMergedChildContext || Vf;
        Xf = H.current;
        G(H, a);
        G(Wf, Wf.current);
        return true;
      }
      function dg(a, b, c) {
        var d = a.stateNode;
        if (!d) throw Error(p(169));
        c ? (a = bg(a, b, Xf), d.__reactInternalMemoizedMergedChildContext = a, E(Wf), E(H), G(H, a)) : E(Wf);
        G(Wf, c);
      }
      var eg = null;
      var fg = false;
      var gg = false;
      function hg(a) {
        null === eg ? eg = [a] : eg.push(a);
      }
      function ig(a) {
        fg = true;
        hg(a);
      }
      function jg() {
        if (!gg && null !== eg) {
          gg = true;
          var a = 0, b = C;
          try {
            var c = eg;
            for (C = 1; a < c.length; a++) {
              var d = c[a];
              do
                d = d(true);
              while (null !== d);
            }
            eg = null;
            fg = false;
          } catch (e) {
            throw null !== eg && (eg = eg.slice(a + 1)), ac(fc, jg), e;
          } finally {
            C = b, gg = false;
          }
        }
        return null;
      }
      var kg = [];
      var lg = 0;
      var mg = null;
      var ng = 0;
      var og = [];
      var pg = 0;
      var qg = null;
      var rg = 1;
      var sg = "";
      function tg(a, b) {
        kg[lg++] = ng;
        kg[lg++] = mg;
        mg = a;
        ng = b;
      }
      function ug(a, b, c) {
        og[pg++] = rg;
        og[pg++] = sg;
        og[pg++] = qg;
        qg = a;
        var d = rg;
        a = sg;
        var e = 32 - oc(d) - 1;
        d &= ~(1 << e);
        c += 1;
        var f = 32 - oc(b) + e;
        if (30 < f) {
          var g = e - e % 5;
          f = (d & (1 << g) - 1).toString(32);
          d >>= g;
          e -= g;
          rg = 1 << 32 - oc(b) + e | c << e | d;
          sg = f + a;
        } else rg = 1 << f | c << e | d, sg = a;
      }
      function vg(a) {
        null !== a.return && (tg(a, 1), ug(a, 1, 0));
      }
      function wg(a) {
        for (; a === mg; ) mg = kg[--lg], kg[lg] = null, ng = kg[--lg], kg[lg] = null;
        for (; a === qg; ) qg = og[--pg], og[pg] = null, sg = og[--pg], og[pg] = null, rg = og[--pg], og[pg] = null;
      }
      var xg = null;
      var yg = null;
      var I = false;
      var zg = null;
      function Ag(a, b) {
        var c = Bg(5, null, null, 0);
        c.elementType = "DELETED";
        c.stateNode = b;
        c.return = a;
        b = a.deletions;
        null === b ? (a.deletions = [c], a.flags |= 16) : b.push(c);
      }
      function Cg(a, b) {
        switch (a.tag) {
          case 5:
            var c = a.type;
            b = 1 !== b.nodeType || c.toLowerCase() !== b.nodeName.toLowerCase() ? null : b;
            return null !== b ? (a.stateNode = b, xg = a, yg = Lf(b.firstChild), true) : false;
          case 6:
            return b = "" === a.pendingProps || 3 !== b.nodeType ? null : b, null !== b ? (a.stateNode = b, xg = a, yg = null, true) : false;
          case 13:
            return b = 8 !== b.nodeType ? null : b, null !== b ? (c = null !== qg ? { id: rg, overflow: sg } : null, a.memoizedState = { dehydrated: b, treeContext: c, retryLane: 1073741824 }, c = Bg(18, null, null, 0), c.stateNode = b, c.return = a, a.child = c, xg = a, yg = null, true) : false;
          default:
            return false;
        }
      }
      function Dg(a) {
        return 0 !== (a.mode & 1) && 0 === (a.flags & 128);
      }
      function Eg(a) {
        if (I) {
          var b = yg;
          if (b) {
            var c = b;
            if (!Cg(a, b)) {
              if (Dg(a)) throw Error(p(418));
              b = Lf(c.nextSibling);
              var d = xg;
              b && Cg(a, b) ? Ag(d, c) : (a.flags = a.flags & -4097 | 2, I = false, xg = a);
            }
          } else {
            if (Dg(a)) throw Error(p(418));
            a.flags = a.flags & -4097 | 2;
            I = false;
            xg = a;
          }
        }
      }
      function Fg(a) {
        for (a = a.return; null !== a && 5 !== a.tag && 3 !== a.tag && 13 !== a.tag; ) a = a.return;
        xg = a;
      }
      function Gg(a) {
        if (a !== xg) return false;
        if (!I) return Fg(a), I = true, false;
        var b;
        (b = 3 !== a.tag) && !(b = 5 !== a.tag) && (b = a.type, b = "head" !== b && "body" !== b && !Ef(a.type, a.memoizedProps));
        if (b && (b = yg)) {
          if (Dg(a)) throw Hg(), Error(p(418));
          for (; b; ) Ag(a, b), b = Lf(b.nextSibling);
        }
        Fg(a);
        if (13 === a.tag) {
          a = a.memoizedState;
          a = null !== a ? a.dehydrated : null;
          if (!a) throw Error(p(317));
          a: {
            a = a.nextSibling;
            for (b = 0; a; ) {
              if (8 === a.nodeType) {
                var c = a.data;
                if ("/$" === c) {
                  if (0 === b) {
                    yg = Lf(a.nextSibling);
                    break a;
                  }
                  b--;
                } else "$" !== c && "$!" !== c && "$?" !== c || b++;
              }
              a = a.nextSibling;
            }
            yg = null;
          }
        } else yg = xg ? Lf(a.stateNode.nextSibling) : null;
        return true;
      }
      function Hg() {
        for (var a = yg; a; ) a = Lf(a.nextSibling);
      }
      function Ig() {
        yg = xg = null;
        I = false;
      }
      function Jg(a) {
        null === zg ? zg = [a] : zg.push(a);
      }
      var Kg = ua.ReactCurrentBatchConfig;
      function Lg(a, b, c) {
        a = c.ref;
        if (null !== a && "function" !== typeof a && "object" !== typeof a) {
          if (c._owner) {
            c = c._owner;
            if (c) {
              if (1 !== c.tag) throw Error(p(309));
              var d = c.stateNode;
            }
            if (!d) throw Error(p(147, a));
            var e = d, f = "" + a;
            if (null !== b && null !== b.ref && "function" === typeof b.ref && b.ref._stringRef === f) return b.ref;
            b = function(a2) {
              var b2 = e.refs;
              null === a2 ? delete b2[f] : b2[f] = a2;
            };
            b._stringRef = f;
            return b;
          }
          if ("string" !== typeof a) throw Error(p(284));
          if (!c._owner) throw Error(p(290, a));
        }
        return a;
      }
      function Mg(a, b) {
        a = Object.prototype.toString.call(b);
        throw Error(p(31, "[object Object]" === a ? "object with keys {" + Object.keys(b).join(", ") + "}" : a));
      }
      function Ng(a) {
        var b = a._init;
        return b(a._payload);
      }
      function Og(a) {
        function b(b2, c2) {
          if (a) {
            var d2 = b2.deletions;
            null === d2 ? (b2.deletions = [c2], b2.flags |= 16) : d2.push(c2);
          }
        }
        function c(c2, d2) {
          if (!a) return null;
          for (; null !== d2; ) b(c2, d2), d2 = d2.sibling;
          return null;
        }
        function d(a2, b2) {
          for (a2 = /* @__PURE__ */ new Map(); null !== b2; ) null !== b2.key ? a2.set(b2.key, b2) : a2.set(b2.index, b2), b2 = b2.sibling;
          return a2;
        }
        function e(a2, b2) {
          a2 = Pg(a2, b2);
          a2.index = 0;
          a2.sibling = null;
          return a2;
        }
        function f(b2, c2, d2) {
          b2.index = d2;
          if (!a) return b2.flags |= 1048576, c2;
          d2 = b2.alternate;
          if (null !== d2) return d2 = d2.index, d2 < c2 ? (b2.flags |= 2, c2) : d2;
          b2.flags |= 2;
          return c2;
        }
        function g(b2) {
          a && null === b2.alternate && (b2.flags |= 2);
          return b2;
        }
        function h(a2, b2, c2, d2) {
          if (null === b2 || 6 !== b2.tag) return b2 = Qg(c2, a2.mode, d2), b2.return = a2, b2;
          b2 = e(b2, c2);
          b2.return = a2;
          return b2;
        }
        function k(a2, b2, c2, d2) {
          var f2 = c2.type;
          if (f2 === ya) return m(a2, b2, c2.props.children, d2, c2.key);
          if (null !== b2 && (b2.elementType === f2 || "object" === typeof f2 && null !== f2 && f2.$$typeof === Ha && Ng(f2) === b2.type)) return d2 = e(b2, c2.props), d2.ref = Lg(a2, b2, c2), d2.return = a2, d2;
          d2 = Rg(c2.type, c2.key, c2.props, null, a2.mode, d2);
          d2.ref = Lg(a2, b2, c2);
          d2.return = a2;
          return d2;
        }
        function l(a2, b2, c2, d2) {
          if (null === b2 || 4 !== b2.tag || b2.stateNode.containerInfo !== c2.containerInfo || b2.stateNode.implementation !== c2.implementation) return b2 = Sg(c2, a2.mode, d2), b2.return = a2, b2;
          b2 = e(b2, c2.children || []);
          b2.return = a2;
          return b2;
        }
        function m(a2, b2, c2, d2, f2) {
          if (null === b2 || 7 !== b2.tag) return b2 = Tg(c2, a2.mode, d2, f2), b2.return = a2, b2;
          b2 = e(b2, c2);
          b2.return = a2;
          return b2;
        }
        function q(a2, b2, c2) {
          if ("string" === typeof b2 && "" !== b2 || "number" === typeof b2) return b2 = Qg("" + b2, a2.mode, c2), b2.return = a2, b2;
          if ("object" === typeof b2 && null !== b2) {
            switch (b2.$$typeof) {
              case va:
                return c2 = Rg(b2.type, b2.key, b2.props, null, a2.mode, c2), c2.ref = Lg(a2, null, b2), c2.return = a2, c2;
              case wa:
                return b2 = Sg(b2, a2.mode, c2), b2.return = a2, b2;
              case Ha:
                var d2 = b2._init;
                return q(a2, d2(b2._payload), c2);
            }
            if (eb(b2) || Ka(b2)) return b2 = Tg(b2, a2.mode, c2, null), b2.return = a2, b2;
            Mg(a2, b2);
          }
          return null;
        }
        function r(a2, b2, c2, d2) {
          var e2 = null !== b2 ? b2.key : null;
          if ("string" === typeof c2 && "" !== c2 || "number" === typeof c2) return null !== e2 ? null : h(a2, b2, "" + c2, d2);
          if ("object" === typeof c2 && null !== c2) {
            switch (c2.$$typeof) {
              case va:
                return c2.key === e2 ? k(a2, b2, c2, d2) : null;
              case wa:
                return c2.key === e2 ? l(a2, b2, c2, d2) : null;
              case Ha:
                return e2 = c2._init, r(
                  a2,
                  b2,
                  e2(c2._payload),
                  d2
                );
            }
            if (eb(c2) || Ka(c2)) return null !== e2 ? null : m(a2, b2, c2, d2, null);
            Mg(a2, c2);
          }
          return null;
        }
        function y(a2, b2, c2, d2, e2) {
          if ("string" === typeof d2 && "" !== d2 || "number" === typeof d2) return a2 = a2.get(c2) || null, h(b2, a2, "" + d2, e2);
          if ("object" === typeof d2 && null !== d2) {
            switch (d2.$$typeof) {
              case va:
                return a2 = a2.get(null === d2.key ? c2 : d2.key) || null, k(b2, a2, d2, e2);
              case wa:
                return a2 = a2.get(null === d2.key ? c2 : d2.key) || null, l(b2, a2, d2, e2);
              case Ha:
                var f2 = d2._init;
                return y(a2, b2, c2, f2(d2._payload), e2);
            }
            if (eb(d2) || Ka(d2)) return a2 = a2.get(c2) || null, m(b2, a2, d2, e2, null);
            Mg(b2, d2);
          }
          return null;
        }
        function n(e2, g2, h2, k2) {
          for (var l2 = null, m2 = null, u = g2, w = g2 = 0, x = null; null !== u && w < h2.length; w++) {
            u.index > w ? (x = u, u = null) : x = u.sibling;
            var n2 = r(e2, u, h2[w], k2);
            if (null === n2) {
              null === u && (u = x);
              break;
            }
            a && u && null === n2.alternate && b(e2, u);
            g2 = f(n2, g2, w);
            null === m2 ? l2 = n2 : m2.sibling = n2;
            m2 = n2;
            u = x;
          }
          if (w === h2.length) return c(e2, u), I && tg(e2, w), l2;
          if (null === u) {
            for (; w < h2.length; w++) u = q(e2, h2[w], k2), null !== u && (g2 = f(u, g2, w), null === m2 ? l2 = u : m2.sibling = u, m2 = u);
            I && tg(e2, w);
            return l2;
          }
          for (u = d(e2, u); w < h2.length; w++) x = y(u, e2, w, h2[w], k2), null !== x && (a && null !== x.alternate && u.delete(null === x.key ? w : x.key), g2 = f(x, g2, w), null === m2 ? l2 = x : m2.sibling = x, m2 = x);
          a && u.forEach(function(a2) {
            return b(e2, a2);
          });
          I && tg(e2, w);
          return l2;
        }
        function t(e2, g2, h2, k2) {
          var l2 = Ka(h2);
          if ("function" !== typeof l2) throw Error(p(150));
          h2 = l2.call(h2);
          if (null == h2) throw Error(p(151));
          for (var u = l2 = null, m2 = g2, w = g2 = 0, x = null, n2 = h2.next(); null !== m2 && !n2.done; w++, n2 = h2.next()) {
            m2.index > w ? (x = m2, m2 = null) : x = m2.sibling;
            var t2 = r(e2, m2, n2.value, k2);
            if (null === t2) {
              null === m2 && (m2 = x);
              break;
            }
            a && m2 && null === t2.alternate && b(e2, m2);
            g2 = f(t2, g2, w);
            null === u ? l2 = t2 : u.sibling = t2;
            u = t2;
            m2 = x;
          }
          if (n2.done) return c(
            e2,
            m2
          ), I && tg(e2, w), l2;
          if (null === m2) {
            for (; !n2.done; w++, n2 = h2.next()) n2 = q(e2, n2.value, k2), null !== n2 && (g2 = f(n2, g2, w), null === u ? l2 = n2 : u.sibling = n2, u = n2);
            I && tg(e2, w);
            return l2;
          }
          for (m2 = d(e2, m2); !n2.done; w++, n2 = h2.next()) n2 = y(m2, e2, w, n2.value, k2), null !== n2 && (a && null !== n2.alternate && m2.delete(null === n2.key ? w : n2.key), g2 = f(n2, g2, w), null === u ? l2 = n2 : u.sibling = n2, u = n2);
          a && m2.forEach(function(a2) {
            return b(e2, a2);
          });
          I && tg(e2, w);
          return l2;
        }
        function J(a2, d2, f2, h2) {
          "object" === typeof f2 && null !== f2 && f2.type === ya && null === f2.key && (f2 = f2.props.children);
          if ("object" === typeof f2 && null !== f2) {
            switch (f2.$$typeof) {
              case va:
                a: {
                  for (var k2 = f2.key, l2 = d2; null !== l2; ) {
                    if (l2.key === k2) {
                      k2 = f2.type;
                      if (k2 === ya) {
                        if (7 === l2.tag) {
                          c(a2, l2.sibling);
                          d2 = e(l2, f2.props.children);
                          d2.return = a2;
                          a2 = d2;
                          break a;
                        }
                      } else if (l2.elementType === k2 || "object" === typeof k2 && null !== k2 && k2.$$typeof === Ha && Ng(k2) === l2.type) {
                        c(a2, l2.sibling);
                        d2 = e(l2, f2.props);
                        d2.ref = Lg(a2, l2, f2);
                        d2.return = a2;
                        a2 = d2;
                        break a;
                      }
                      c(a2, l2);
                      break;
                    } else b(a2, l2);
                    l2 = l2.sibling;
                  }
                  f2.type === ya ? (d2 = Tg(f2.props.children, a2.mode, h2, f2.key), d2.return = a2, a2 = d2) : (h2 = Rg(f2.type, f2.key, f2.props, null, a2.mode, h2), h2.ref = Lg(a2, d2, f2), h2.return = a2, a2 = h2);
                }
                return g(a2);
              case wa:
                a: {
                  for (l2 = f2.key; null !== d2; ) {
                    if (d2.key === l2) if (4 === d2.tag && d2.stateNode.containerInfo === f2.containerInfo && d2.stateNode.implementation === f2.implementation) {
                      c(a2, d2.sibling);
                      d2 = e(d2, f2.children || []);
                      d2.return = a2;
                      a2 = d2;
                      break a;
                    } else {
                      c(a2, d2);
                      break;
                    }
                    else b(a2, d2);
                    d2 = d2.sibling;
                  }
                  d2 = Sg(f2, a2.mode, h2);
                  d2.return = a2;
                  a2 = d2;
                }
                return g(a2);
              case Ha:
                return l2 = f2._init, J(a2, d2, l2(f2._payload), h2);
            }
            if (eb(f2)) return n(a2, d2, f2, h2);
            if (Ka(f2)) return t(a2, d2, f2, h2);
            Mg(a2, f2);
          }
          return "string" === typeof f2 && "" !== f2 || "number" === typeof f2 ? (f2 = "" + f2, null !== d2 && 6 === d2.tag ? (c(a2, d2.sibling), d2 = e(d2, f2), d2.return = a2, a2 = d2) : (c(a2, d2), d2 = Qg(f2, a2.mode, h2), d2.return = a2, a2 = d2), g(a2)) : c(a2, d2);
        }
        return J;
      }
      var Ug = Og(true);
      var Vg = Og(false);
      var Wg = Uf(null);
      var Xg = null;
      var Yg = null;
      var Zg = null;
      function $g() {
        Zg = Yg = Xg = null;
      }
      function ah(a) {
        var b = Wg.current;
        E(Wg);
        a._currentValue = b;
      }
      function bh(a, b, c) {
        for (; null !== a; ) {
          var d = a.alternate;
          (a.childLanes & b) !== b ? (a.childLanes |= b, null !== d && (d.childLanes |= b)) : null !== d && (d.childLanes & b) !== b && (d.childLanes |= b);
          if (a === c) break;
          a = a.return;
        }
      }
      function ch(a, b) {
        Xg = a;
        Zg = Yg = null;
        a = a.dependencies;
        null !== a && null !== a.firstContext && (0 !== (a.lanes & b) && (dh = true), a.firstContext = null);
      }
      function eh(a) {
        var b = a._currentValue;
        if (Zg !== a) if (a = { context: a, memoizedValue: b, next: null }, null === Yg) {
          if (null === Xg) throw Error(p(308));
          Yg = a;
          Xg.dependencies = { lanes: 0, firstContext: a };
        } else Yg = Yg.next = a;
        return b;
      }
      var fh = null;
      function gh(a) {
        null === fh ? fh = [a] : fh.push(a);
      }
      function hh(a, b, c, d) {
        var e = b.interleaved;
        null === e ? (c.next = c, gh(b)) : (c.next = e.next, e.next = c);
        b.interleaved = c;
        return ih(a, d);
      }
      function ih(a, b) {
        a.lanes |= b;
        var c = a.alternate;
        null !== c && (c.lanes |= b);
        c = a;
        for (a = a.return; null !== a; ) a.childLanes |= b, c = a.alternate, null !== c && (c.childLanes |= b), c = a, a = a.return;
        return 3 === c.tag ? c.stateNode : null;
      }
      var jh = false;
      function kh(a) {
        a.updateQueue = { baseState: a.memoizedState, firstBaseUpdate: null, lastBaseUpdate: null, shared: { pending: null, interleaved: null, lanes: 0 }, effects: null };
      }
      function lh(a, b) {
        a = a.updateQueue;
        b.updateQueue === a && (b.updateQueue = { baseState: a.baseState, firstBaseUpdate: a.firstBaseUpdate, lastBaseUpdate: a.lastBaseUpdate, shared: a.shared, effects: a.effects });
      }
      function mh(a, b) {
        return { eventTime: a, lane: b, tag: 0, payload: null, callback: null, next: null };
      }
      function nh(a, b, c) {
        var d = a.updateQueue;
        if (null === d) return null;
        d = d.shared;
        if (0 !== (K & 2)) {
          var e = d.pending;
          null === e ? b.next = b : (b.next = e.next, e.next = b);
          d.pending = b;
          return ih(a, c);
        }
        e = d.interleaved;
        null === e ? (b.next = b, gh(d)) : (b.next = e.next, e.next = b);
        d.interleaved = b;
        return ih(a, c);
      }
      function oh(a, b, c) {
        b = b.updateQueue;
        if (null !== b && (b = b.shared, 0 !== (c & 4194240))) {
          var d = b.lanes;
          d &= a.pendingLanes;
          c |= d;
          b.lanes = c;
          Cc(a, c);
        }
      }
      function ph(a, b) {
        var c = a.updateQueue, d = a.alternate;
        if (null !== d && (d = d.updateQueue, c === d)) {
          var e = null, f = null;
          c = c.firstBaseUpdate;
          if (null !== c) {
            do {
              var g = { eventTime: c.eventTime, lane: c.lane, tag: c.tag, payload: c.payload, callback: c.callback, next: null };
              null === f ? e = f = g : f = f.next = g;
              c = c.next;
            } while (null !== c);
            null === f ? e = f = b : f = f.next = b;
          } else e = f = b;
          c = { baseState: d.baseState, firstBaseUpdate: e, lastBaseUpdate: f, shared: d.shared, effects: d.effects };
          a.updateQueue = c;
          return;
        }
        a = c.lastBaseUpdate;
        null === a ? c.firstBaseUpdate = b : a.next = b;
        c.lastBaseUpdate = b;
      }
      function qh(a, b, c, d) {
        var e = a.updateQueue;
        jh = false;
        var f = e.firstBaseUpdate, g = e.lastBaseUpdate, h = e.shared.pending;
        if (null !== h) {
          e.shared.pending = null;
          var k = h, l = k.next;
          k.next = null;
          null === g ? f = l : g.next = l;
          g = k;
          var m = a.alternate;
          null !== m && (m = m.updateQueue, h = m.lastBaseUpdate, h !== g && (null === h ? m.firstBaseUpdate = l : h.next = l, m.lastBaseUpdate = k));
        }
        if (null !== f) {
          var q = e.baseState;
          g = 0;
          m = l = k = null;
          h = f;
          do {
            var r = h.lane, y = h.eventTime;
            if ((d & r) === r) {
              null !== m && (m = m.next = {
                eventTime: y,
                lane: 0,
                tag: h.tag,
                payload: h.payload,
                callback: h.callback,
                next: null
              });
              a: {
                var n = a, t = h;
                r = b;
                y = c;
                switch (t.tag) {
                  case 1:
                    n = t.payload;
                    if ("function" === typeof n) {
                      q = n.call(y, q, r);
                      break a;
                    }
                    q = n;
                    break a;
                  case 3:
                    n.flags = n.flags & -65537 | 128;
                  case 0:
                    n = t.payload;
                    r = "function" === typeof n ? n.call(y, q, r) : n;
                    if (null === r || void 0 === r) break a;
                    q = A({}, q, r);
                    break a;
                  case 2:
                    jh = true;
                }
              }
              null !== h.callback && 0 !== h.lane && (a.flags |= 64, r = e.effects, null === r ? e.effects = [h] : r.push(h));
            } else y = { eventTime: y, lane: r, tag: h.tag, payload: h.payload, callback: h.callback, next: null }, null === m ? (l = m = y, k = q) : m = m.next = y, g |= r;
            h = h.next;
            if (null === h) if (h = e.shared.pending, null === h) break;
            else r = h, h = r.next, r.next = null, e.lastBaseUpdate = r, e.shared.pending = null;
          } while (1);
          null === m && (k = q);
          e.baseState = k;
          e.firstBaseUpdate = l;
          e.lastBaseUpdate = m;
          b = e.shared.interleaved;
          if (null !== b) {
            e = b;
            do
              g |= e.lane, e = e.next;
            while (e !== b);
          } else null === f && (e.shared.lanes = 0);
          rh |= g;
          a.lanes = g;
          a.memoizedState = q;
        }
      }
      function sh(a, b, c) {
        a = b.effects;
        b.effects = null;
        if (null !== a) for (b = 0; b < a.length; b++) {
          var d = a[b], e = d.callback;
          if (null !== e) {
            d.callback = null;
            d = c;
            if ("function" !== typeof e) throw Error(p(191, e));
            e.call(d);
          }
        }
      }
      var th = {};
      var uh = Uf(th);
      var vh = Uf(th);
      var wh = Uf(th);
      function xh(a) {
        if (a === th) throw Error(p(174));
        return a;
      }
      function yh(a, b) {
        G(wh, b);
        G(vh, a);
        G(uh, th);
        a = b.nodeType;
        switch (a) {
          case 9:
          case 11:
            b = (b = b.documentElement) ? b.namespaceURI : lb(null, "");
            break;
          default:
            a = 8 === a ? b.parentNode : b, b = a.namespaceURI || null, a = a.tagName, b = lb(b, a);
        }
        E(uh);
        G(uh, b);
      }
      function zh() {
        E(uh);
        E(vh);
        E(wh);
      }
      function Ah(a) {
        xh(wh.current);
        var b = xh(uh.current);
        var c = lb(b, a.type);
        b !== c && (G(vh, a), G(uh, c));
      }
      function Bh(a) {
        vh.current === a && (E(uh), E(vh));
      }
      var L = Uf(0);
      function Ch(a) {
        for (var b = a; null !== b; ) {
          if (13 === b.tag) {
            var c = b.memoizedState;
            if (null !== c && (c = c.dehydrated, null === c || "$?" === c.data || "$!" === c.data)) return b;
          } else if (19 === b.tag && void 0 !== b.memoizedProps.revealOrder) {
            if (0 !== (b.flags & 128)) return b;
          } else if (null !== b.child) {
            b.child.return = b;
            b = b.child;
            continue;
          }
          if (b === a) break;
          for (; null === b.sibling; ) {
            if (null === b.return || b.return === a) return null;
            b = b.return;
          }
          b.sibling.return = b.return;
          b = b.sibling;
        }
        return null;
      }
      var Dh = [];
      function Eh() {
        for (var a = 0; a < Dh.length; a++) Dh[a]._workInProgressVersionPrimary = null;
        Dh.length = 0;
      }
      var Fh = ua.ReactCurrentDispatcher;
      var Gh = ua.ReactCurrentBatchConfig;
      var Hh = 0;
      var M = null;
      var N = null;
      var O = null;
      var Ih = false;
      var Jh = false;
      var Kh = 0;
      var Lh = 0;
      function P() {
        throw Error(p(321));
      }
      function Mh(a, b) {
        if (null === b) return false;
        for (var c = 0; c < b.length && c < a.length; c++) if (!He(a[c], b[c])) return false;
        return true;
      }
      function Nh(a, b, c, d, e, f) {
        Hh = f;
        M = b;
        b.memoizedState = null;
        b.updateQueue = null;
        b.lanes = 0;
        Fh.current = null === a || null === a.memoizedState ? Oh : Ph;
        a = c(d, e);
        if (Jh) {
          f = 0;
          do {
            Jh = false;
            Kh = 0;
            if (25 <= f) throw Error(p(301));
            f += 1;
            O = N = null;
            b.updateQueue = null;
            Fh.current = Qh;
            a = c(d, e);
          } while (Jh);
        }
        Fh.current = Rh;
        b = null !== N && null !== N.next;
        Hh = 0;
        O = N = M = null;
        Ih = false;
        if (b) throw Error(p(300));
        return a;
      }
      function Sh() {
        var a = 0 !== Kh;
        Kh = 0;
        return a;
      }
      function Th() {
        var a = { memoizedState: null, baseState: null, baseQueue: null, queue: null, next: null };
        null === O ? M.memoizedState = O = a : O = O.next = a;
        return O;
      }
      function Uh() {
        if (null === N) {
          var a = M.alternate;
          a = null !== a ? a.memoizedState : null;
        } else a = N.next;
        var b = null === O ? M.memoizedState : O.next;
        if (null !== b) O = b, N = a;
        else {
          if (null === a) throw Error(p(310));
          N = a;
          a = { memoizedState: N.memoizedState, baseState: N.baseState, baseQueue: N.baseQueue, queue: N.queue, next: null };
          null === O ? M.memoizedState = O = a : O = O.next = a;
        }
        return O;
      }
      function Vh(a, b) {
        return "function" === typeof b ? b(a) : b;
      }
      function Wh(a) {
        var b = Uh(), c = b.queue;
        if (null === c) throw Error(p(311));
        c.lastRenderedReducer = a;
        var d = N, e = d.baseQueue, f = c.pending;
        if (null !== f) {
          if (null !== e) {
            var g = e.next;
            e.next = f.next;
            f.next = g;
          }
          d.baseQueue = e = f;
          c.pending = null;
        }
        if (null !== e) {
          f = e.next;
          d = d.baseState;
          var h = g = null, k = null, l = f;
          do {
            var m = l.lane;
            if ((Hh & m) === m) null !== k && (k = k.next = { lane: 0, action: l.action, hasEagerState: l.hasEagerState, eagerState: l.eagerState, next: null }), d = l.hasEagerState ? l.eagerState : a(d, l.action);
            else {
              var q = {
                lane: m,
                action: l.action,
                hasEagerState: l.hasEagerState,
                eagerState: l.eagerState,
                next: null
              };
              null === k ? (h = k = q, g = d) : k = k.next = q;
              M.lanes |= m;
              rh |= m;
            }
            l = l.next;
          } while (null !== l && l !== f);
          null === k ? g = d : k.next = h;
          He(d, b.memoizedState) || (dh = true);
          b.memoizedState = d;
          b.baseState = g;
          b.baseQueue = k;
          c.lastRenderedState = d;
        }
        a = c.interleaved;
        if (null !== a) {
          e = a;
          do
            f = e.lane, M.lanes |= f, rh |= f, e = e.next;
          while (e !== a);
        } else null === e && (c.lanes = 0);
        return [b.memoizedState, c.dispatch];
      }
      function Xh(a) {
        var b = Uh(), c = b.queue;
        if (null === c) throw Error(p(311));
        c.lastRenderedReducer = a;
        var d = c.dispatch, e = c.pending, f = b.memoizedState;
        if (null !== e) {
          c.pending = null;
          var g = e = e.next;
          do
            f = a(f, g.action), g = g.next;
          while (g !== e);
          He(f, b.memoizedState) || (dh = true);
          b.memoizedState = f;
          null === b.baseQueue && (b.baseState = f);
          c.lastRenderedState = f;
        }
        return [f, d];
      }
      function Yh() {
      }
      function Zh(a, b) {
        var c = M, d = Uh(), e = b(), f = !He(d.memoizedState, e);
        f && (d.memoizedState = e, dh = true);
        d = d.queue;
        $h(ai.bind(null, c, d, a), [a]);
        if (d.getSnapshot !== b || f || null !== O && O.memoizedState.tag & 1) {
          c.flags |= 2048;
          bi(9, ci.bind(null, c, d, e, b), void 0, null);
          if (null === Q) throw Error(p(349));
          0 !== (Hh & 30) || di(c, b, e);
        }
        return e;
      }
      function di(a, b, c) {
        a.flags |= 16384;
        a = { getSnapshot: b, value: c };
        b = M.updateQueue;
        null === b ? (b = { lastEffect: null, stores: null }, M.updateQueue = b, b.stores = [a]) : (c = b.stores, null === c ? b.stores = [a] : c.push(a));
      }
      function ci(a, b, c, d) {
        b.value = c;
        b.getSnapshot = d;
        ei(b) && fi(a);
      }
      function ai(a, b, c) {
        return c(function() {
          ei(b) && fi(a);
        });
      }
      function ei(a) {
        var b = a.getSnapshot;
        a = a.value;
        try {
          var c = b();
          return !He(a, c);
        } catch (d) {
          return true;
        }
      }
      function fi(a) {
        var b = ih(a, 1);
        null !== b && gi(b, a, 1, -1);
      }
      function hi(a) {
        var b = Th();
        "function" === typeof a && (a = a());
        b.memoizedState = b.baseState = a;
        a = { pending: null, interleaved: null, lanes: 0, dispatch: null, lastRenderedReducer: Vh, lastRenderedState: a };
        b.queue = a;
        a = a.dispatch = ii.bind(null, M, a);
        return [b.memoizedState, a];
      }
      function bi(a, b, c, d) {
        a = { tag: a, create: b, destroy: c, deps: d, next: null };
        b = M.updateQueue;
        null === b ? (b = { lastEffect: null, stores: null }, M.updateQueue = b, b.lastEffect = a.next = a) : (c = b.lastEffect, null === c ? b.lastEffect = a.next = a : (d = c.next, c.next = a, a.next = d, b.lastEffect = a));
        return a;
      }
      function ji() {
        return Uh().memoizedState;
      }
      function ki(a, b, c, d) {
        var e = Th();
        M.flags |= a;
        e.memoizedState = bi(1 | b, c, void 0, void 0 === d ? null : d);
      }
      function li(a, b, c, d) {
        var e = Uh();
        d = void 0 === d ? null : d;
        var f = void 0;
        if (null !== N) {
          var g = N.memoizedState;
          f = g.destroy;
          if (null !== d && Mh(d, g.deps)) {
            e.memoizedState = bi(b, c, f, d);
            return;
          }
        }
        M.flags |= a;
        e.memoizedState = bi(1 | b, c, f, d);
      }
      function mi(a, b) {
        return ki(8390656, 8, a, b);
      }
      function $h(a, b) {
        return li(2048, 8, a, b);
      }
      function ni(a, b) {
        return li(4, 2, a, b);
      }
      function oi(a, b) {
        return li(4, 4, a, b);
      }
      function pi(a, b) {
        if ("function" === typeof b) return a = a(), b(a), function() {
          b(null);
        };
        if (null !== b && void 0 !== b) return a = a(), b.current = a, function() {
          b.current = null;
        };
      }
      function qi(a, b, c) {
        c = null !== c && void 0 !== c ? c.concat([a]) : null;
        return li(4, 4, pi.bind(null, b, a), c);
      }
      function ri() {
      }
      function si(a, b) {
        var c = Uh();
        b = void 0 === b ? null : b;
        var d = c.memoizedState;
        if (null !== d && null !== b && Mh(b, d[1])) return d[0];
        c.memoizedState = [a, b];
        return a;
      }
      function ti(a, b) {
        var c = Uh();
        b = void 0 === b ? null : b;
        var d = c.memoizedState;
        if (null !== d && null !== b && Mh(b, d[1])) return d[0];
        a = a();
        c.memoizedState = [a, b];
        return a;
      }
      function ui(a, b, c) {
        if (0 === (Hh & 21)) return a.baseState && (a.baseState = false, dh = true), a.memoizedState = c;
        He(c, b) || (c = yc(), M.lanes |= c, rh |= c, a.baseState = true);
        return b;
      }
      function vi(a, b) {
        var c = C;
        C = 0 !== c && 4 > c ? c : 4;
        a(true);
        var d = Gh.transition;
        Gh.transition = {};
        try {
          a(false), b();
        } finally {
          C = c, Gh.transition = d;
        }
      }
      function wi() {
        return Uh().memoizedState;
      }
      function xi(a, b, c) {
        var d = yi(a);
        c = { lane: d, action: c, hasEagerState: false, eagerState: null, next: null };
        if (zi(a)) Ai(b, c);
        else if (c = hh(a, b, c, d), null !== c) {
          var e = R();
          gi(c, a, d, e);
          Bi(c, b, d);
        }
      }
      function ii(a, b, c) {
        var d = yi(a), e = { lane: d, action: c, hasEagerState: false, eagerState: null, next: null };
        if (zi(a)) Ai(b, e);
        else {
          var f = a.alternate;
          if (0 === a.lanes && (null === f || 0 === f.lanes) && (f = b.lastRenderedReducer, null !== f)) try {
            var g = b.lastRenderedState, h = f(g, c);
            e.hasEagerState = true;
            e.eagerState = h;
            if (He(h, g)) {
              var k = b.interleaved;
              null === k ? (e.next = e, gh(b)) : (e.next = k.next, k.next = e);
              b.interleaved = e;
              return;
            }
          } catch (l) {
          } finally {
          }
          c = hh(a, b, e, d);
          null !== c && (e = R(), gi(c, a, d, e), Bi(c, b, d));
        }
      }
      function zi(a) {
        var b = a.alternate;
        return a === M || null !== b && b === M;
      }
      function Ai(a, b) {
        Jh = Ih = true;
        var c = a.pending;
        null === c ? b.next = b : (b.next = c.next, c.next = b);
        a.pending = b;
      }
      function Bi(a, b, c) {
        if (0 !== (c & 4194240)) {
          var d = b.lanes;
          d &= a.pendingLanes;
          c |= d;
          b.lanes = c;
          Cc(a, c);
        }
      }
      var Rh = { readContext: eh, useCallback: P, useContext: P, useEffect: P, useImperativeHandle: P, useInsertionEffect: P, useLayoutEffect: P, useMemo: P, useReducer: P, useRef: P, useState: P, useDebugValue: P, useDeferredValue: P, useTransition: P, useMutableSource: P, useSyncExternalStore: P, useId: P, unstable_isNewReconciler: false };
      var Oh = { readContext: eh, useCallback: function(a, b) {
        Th().memoizedState = [a, void 0 === b ? null : b];
        return a;
      }, useContext: eh, useEffect: mi, useImperativeHandle: function(a, b, c) {
        c = null !== c && void 0 !== c ? c.concat([a]) : null;
        return ki(
          4194308,
          4,
          pi.bind(null, b, a),
          c
        );
      }, useLayoutEffect: function(a, b) {
        return ki(4194308, 4, a, b);
      }, useInsertionEffect: function(a, b) {
        return ki(4, 2, a, b);
      }, useMemo: function(a, b) {
        var c = Th();
        b = void 0 === b ? null : b;
        a = a();
        c.memoizedState = [a, b];
        return a;
      }, useReducer: function(a, b, c) {
        var d = Th();
        b = void 0 !== c ? c(b) : b;
        d.memoizedState = d.baseState = b;
        a = { pending: null, interleaved: null, lanes: 0, dispatch: null, lastRenderedReducer: a, lastRenderedState: b };
        d.queue = a;
        a = a.dispatch = xi.bind(null, M, a);
        return [d.memoizedState, a];
      }, useRef: function(a) {
        var b = Th();
        a = { current: a };
        return b.memoizedState = a;
      }, useState: hi, useDebugValue: ri, useDeferredValue: function(a) {
        return Th().memoizedState = a;
      }, useTransition: function() {
        var a = hi(false), b = a[0];
        a = vi.bind(null, a[1]);
        Th().memoizedState = a;
        return [b, a];
      }, useMutableSource: function() {
      }, useSyncExternalStore: function(a, b, c) {
        var d = M, e = Th();
        if (I) {
          if (void 0 === c) throw Error(p(407));
          c = c();
        } else {
          c = b();
          if (null === Q) throw Error(p(349));
          0 !== (Hh & 30) || di(d, b, c);
        }
        e.memoizedState = c;
        var f = { value: c, getSnapshot: b };
        e.queue = f;
        mi(ai.bind(
          null,
          d,
          f,
          a
        ), [a]);
        d.flags |= 2048;
        bi(9, ci.bind(null, d, f, c, b), void 0, null);
        return c;
      }, useId: function() {
        var a = Th(), b = Q.identifierPrefix;
        if (I) {
          var c = sg;
          var d = rg;
          c = (d & ~(1 << 32 - oc(d) - 1)).toString(32) + c;
          b = ":" + b + "R" + c;
          c = Kh++;
          0 < c && (b += "H" + c.toString(32));
          b += ":";
        } else c = Lh++, b = ":" + b + "r" + c.toString(32) + ":";
        return a.memoizedState = b;
      }, unstable_isNewReconciler: false };
      var Ph = {
        readContext: eh,
        useCallback: si,
        useContext: eh,
        useEffect: $h,
        useImperativeHandle: qi,
        useInsertionEffect: ni,
        useLayoutEffect: oi,
        useMemo: ti,
        useReducer: Wh,
        useRef: ji,
        useState: function() {
          return Wh(Vh);
        },
        useDebugValue: ri,
        useDeferredValue: function(a) {
          var b = Uh();
          return ui(b, N.memoizedState, a);
        },
        useTransition: function() {
          var a = Wh(Vh)[0], b = Uh().memoizedState;
          return [a, b];
        },
        useMutableSource: Yh,
        useSyncExternalStore: Zh,
        useId: wi,
        unstable_isNewReconciler: false
      };
      var Qh = { readContext: eh, useCallback: si, useContext: eh, useEffect: $h, useImperativeHandle: qi, useInsertionEffect: ni, useLayoutEffect: oi, useMemo: ti, useReducer: Xh, useRef: ji, useState: function() {
        return Xh(Vh);
      }, useDebugValue: ri, useDeferredValue: function(a) {
        var b = Uh();
        return null === N ? b.memoizedState = a : ui(b, N.memoizedState, a);
      }, useTransition: function() {
        var a = Xh(Vh)[0], b = Uh().memoizedState;
        return [a, b];
      }, useMutableSource: Yh, useSyncExternalStore: Zh, useId: wi, unstable_isNewReconciler: false };
      function Ci(a, b) {
        if (a && a.defaultProps) {
          b = A({}, b);
          a = a.defaultProps;
          for (var c in a) void 0 === b[c] && (b[c] = a[c]);
          return b;
        }
        return b;
      }
      function Di(a, b, c, d) {
        b = a.memoizedState;
        c = c(d, b);
        c = null === c || void 0 === c ? b : A({}, b, c);
        a.memoizedState = c;
        0 === a.lanes && (a.updateQueue.baseState = c);
      }
      var Ei = { isMounted: function(a) {
        return (a = a._reactInternals) ? Vb(a) === a : false;
      }, enqueueSetState: function(a, b, c) {
        a = a._reactInternals;
        var d = R(), e = yi(a), f = mh(d, e);
        f.payload = b;
        void 0 !== c && null !== c && (f.callback = c);
        b = nh(a, f, e);
        null !== b && (gi(b, a, e, d), oh(b, a, e));
      }, enqueueReplaceState: function(a, b, c) {
        a = a._reactInternals;
        var d = R(), e = yi(a), f = mh(d, e);
        f.tag = 1;
        f.payload = b;
        void 0 !== c && null !== c && (f.callback = c);
        b = nh(a, f, e);
        null !== b && (gi(b, a, e, d), oh(b, a, e));
      }, enqueueForceUpdate: function(a, b) {
        a = a._reactInternals;
        var c = R(), d = yi(a), e = mh(c, d);
        e.tag = 2;
        void 0 !== b && null !== b && (e.callback = b);
        b = nh(a, e, d);
        null !== b && (gi(b, a, d, c), oh(b, a, d));
      } };
      function Fi(a, b, c, d, e, f, g) {
        a = a.stateNode;
        return "function" === typeof a.shouldComponentUpdate ? a.shouldComponentUpdate(d, f, g) : b.prototype && b.prototype.isPureReactComponent ? !Ie(c, d) || !Ie(e, f) : true;
      }
      function Gi(a, b, c) {
        var d = false, e = Vf;
        var f = b.contextType;
        "object" === typeof f && null !== f ? f = eh(f) : (e = Zf(b) ? Xf : H.current, d = b.contextTypes, f = (d = null !== d && void 0 !== d) ? Yf(a, e) : Vf);
        b = new b(c, f);
        a.memoizedState = null !== b.state && void 0 !== b.state ? b.state : null;
        b.updater = Ei;
        a.stateNode = b;
        b._reactInternals = a;
        d && (a = a.stateNode, a.__reactInternalMemoizedUnmaskedChildContext = e, a.__reactInternalMemoizedMaskedChildContext = f);
        return b;
      }
      function Hi(a, b, c, d) {
        a = b.state;
        "function" === typeof b.componentWillReceiveProps && b.componentWillReceiveProps(c, d);
        "function" === typeof b.UNSAFE_componentWillReceiveProps && b.UNSAFE_componentWillReceiveProps(c, d);
        b.state !== a && Ei.enqueueReplaceState(b, b.state, null);
      }
      function Ii(a, b, c, d) {
        var e = a.stateNode;
        e.props = c;
        e.state = a.memoizedState;
        e.refs = {};
        kh(a);
        var f = b.contextType;
        "object" === typeof f && null !== f ? e.context = eh(f) : (f = Zf(b) ? Xf : H.current, e.context = Yf(a, f));
        e.state = a.memoizedState;
        f = b.getDerivedStateFromProps;
        "function" === typeof f && (Di(a, b, f, c), e.state = a.memoizedState);
        "function" === typeof b.getDerivedStateFromProps || "function" === typeof e.getSnapshotBeforeUpdate || "function" !== typeof e.UNSAFE_componentWillMount && "function" !== typeof e.componentWillMount || (b = e.state, "function" === typeof e.componentWillMount && e.componentWillMount(), "function" === typeof e.UNSAFE_componentWillMount && e.UNSAFE_componentWillMount(), b !== e.state && Ei.enqueueReplaceState(e, e.state, null), qh(a, c, e, d), e.state = a.memoizedState);
        "function" === typeof e.componentDidMount && (a.flags |= 4194308);
      }
      function Ji(a, b) {
        try {
          var c = "", d = b;
          do
            c += Pa(d), d = d.return;
          while (d);
          var e = c;
        } catch (f) {
          e = "\nError generating stack: " + f.message + "\n" + f.stack;
        }
        return { value: a, source: b, stack: e, digest: null };
      }
      function Ki(a, b, c) {
        return { value: a, source: null, stack: null != c ? c : null, digest: null != b ? b : null };
      }
      function Li(a, b) {
        try {
          console.error(b.value);
        } catch (c) {
          setTimeout(function() {
            throw c;
          });
        }
      }
      var Mi = "function" === typeof WeakMap ? WeakMap : Map;
      function Ni(a, b, c) {
        c = mh(-1, c);
        c.tag = 3;
        c.payload = { element: null };
        var d = b.value;
        c.callback = function() {
          Oi || (Oi = true, Pi = d);
          Li(a, b);
        };
        return c;
      }
      function Qi(a, b, c) {
        c = mh(-1, c);
        c.tag = 3;
        var d = a.type.getDerivedStateFromError;
        if ("function" === typeof d) {
          var e = b.value;
          c.payload = function() {
            return d(e);
          };
          c.callback = function() {
            Li(a, b);
          };
        }
        var f = a.stateNode;
        null !== f && "function" === typeof f.componentDidCatch && (c.callback = function() {
          Li(a, b);
          "function" !== typeof d && (null === Ri ? Ri = /* @__PURE__ */ new Set([this]) : Ri.add(this));
          var c2 = b.stack;
          this.componentDidCatch(b.value, { componentStack: null !== c2 ? c2 : "" });
        });
        return c;
      }
      function Si(a, b, c) {
        var d = a.pingCache;
        if (null === d) {
          d = a.pingCache = new Mi();
          var e = /* @__PURE__ */ new Set();
          d.set(b, e);
        } else e = d.get(b), void 0 === e && (e = /* @__PURE__ */ new Set(), d.set(b, e));
        e.has(c) || (e.add(c), a = Ti.bind(null, a, b, c), b.then(a, a));
      }
      function Ui(a) {
        do {
          var b;
          if (b = 13 === a.tag) b = a.memoizedState, b = null !== b ? null !== b.dehydrated ? true : false : true;
          if (b) return a;
          a = a.return;
        } while (null !== a);
        return null;
      }
      function Vi(a, b, c, d, e) {
        if (0 === (a.mode & 1)) return a === b ? a.flags |= 65536 : (a.flags |= 128, c.flags |= 131072, c.flags &= -52805, 1 === c.tag && (null === c.alternate ? c.tag = 17 : (b = mh(-1, 1), b.tag = 2, nh(c, b, 1))), c.lanes |= 1), a;
        a.flags |= 65536;
        a.lanes = e;
        return a;
      }
      var Wi = ua.ReactCurrentOwner;
      var dh = false;
      function Xi(a, b, c, d) {
        b.child = null === a ? Vg(b, null, c, d) : Ug(b, a.child, c, d);
      }
      function Yi(a, b, c, d, e) {
        c = c.render;
        var f = b.ref;
        ch(b, e);
        d = Nh(a, b, c, d, f, e);
        c = Sh();
        if (null !== a && !dh) return b.updateQueue = a.updateQueue, b.flags &= -2053, a.lanes &= ~e, Zi(a, b, e);
        I && c && vg(b);
        b.flags |= 1;
        Xi(a, b, d, e);
        return b.child;
      }
      function $i(a, b, c, d, e) {
        if (null === a) {
          var f = c.type;
          if ("function" === typeof f && !aj(f) && void 0 === f.defaultProps && null === c.compare && void 0 === c.defaultProps) return b.tag = 15, b.type = f, bj(a, b, f, d, e);
          a = Rg(c.type, null, d, b, b.mode, e);
          a.ref = b.ref;
          a.return = b;
          return b.child = a;
        }
        f = a.child;
        if (0 === (a.lanes & e)) {
          var g = f.memoizedProps;
          c = c.compare;
          c = null !== c ? c : Ie;
          if (c(g, d) && a.ref === b.ref) return Zi(a, b, e);
        }
        b.flags |= 1;
        a = Pg(f, d);
        a.ref = b.ref;
        a.return = b;
        return b.child = a;
      }
      function bj(a, b, c, d, e) {
        if (null !== a) {
          var f = a.memoizedProps;
          if (Ie(f, d) && a.ref === b.ref) if (dh = false, b.pendingProps = d = f, 0 !== (a.lanes & e)) 0 !== (a.flags & 131072) && (dh = true);
          else return b.lanes = a.lanes, Zi(a, b, e);
        }
        return cj(a, b, c, d, e);
      }
      function dj(a, b, c) {
        var d = b.pendingProps, e = d.children, f = null !== a ? a.memoizedState : null;
        if ("hidden" === d.mode) if (0 === (b.mode & 1)) b.memoizedState = { baseLanes: 0, cachePool: null, transitions: null }, G(ej, fj), fj |= c;
        else {
          if (0 === (c & 1073741824)) return a = null !== f ? f.baseLanes | c : c, b.lanes = b.childLanes = 1073741824, b.memoizedState = { baseLanes: a, cachePool: null, transitions: null }, b.updateQueue = null, G(ej, fj), fj |= a, null;
          b.memoizedState = { baseLanes: 0, cachePool: null, transitions: null };
          d = null !== f ? f.baseLanes : c;
          G(ej, fj);
          fj |= d;
        }
        else null !== f ? (d = f.baseLanes | c, b.memoizedState = null) : d = c, G(ej, fj), fj |= d;
        Xi(a, b, e, c);
        return b.child;
      }
      function gj(a, b) {
        var c = b.ref;
        if (null === a && null !== c || null !== a && a.ref !== c) b.flags |= 512, b.flags |= 2097152;
      }
      function cj(a, b, c, d, e) {
        var f = Zf(c) ? Xf : H.current;
        f = Yf(b, f);
        ch(b, e);
        c = Nh(a, b, c, d, f, e);
        d = Sh();
        if (null !== a && !dh) return b.updateQueue = a.updateQueue, b.flags &= -2053, a.lanes &= ~e, Zi(a, b, e);
        I && d && vg(b);
        b.flags |= 1;
        Xi(a, b, c, e);
        return b.child;
      }
      function hj(a, b, c, d, e) {
        if (Zf(c)) {
          var f = true;
          cg(b);
        } else f = false;
        ch(b, e);
        if (null === b.stateNode) ij(a, b), Gi(b, c, d), Ii(b, c, d, e), d = true;
        else if (null === a) {
          var g = b.stateNode, h = b.memoizedProps;
          g.props = h;
          var k = g.context, l = c.contextType;
          "object" === typeof l && null !== l ? l = eh(l) : (l = Zf(c) ? Xf : H.current, l = Yf(b, l));
          var m = c.getDerivedStateFromProps, q = "function" === typeof m || "function" === typeof g.getSnapshotBeforeUpdate;
          q || "function" !== typeof g.UNSAFE_componentWillReceiveProps && "function" !== typeof g.componentWillReceiveProps || (h !== d || k !== l) && Hi(b, g, d, l);
          jh = false;
          var r = b.memoizedState;
          g.state = r;
          qh(b, d, g, e);
          k = b.memoizedState;
          h !== d || r !== k || Wf.current || jh ? ("function" === typeof m && (Di(b, c, m, d), k = b.memoizedState), (h = jh || Fi(b, c, h, d, r, k, l)) ? (q || "function" !== typeof g.UNSAFE_componentWillMount && "function" !== typeof g.componentWillMount || ("function" === typeof g.componentWillMount && g.componentWillMount(), "function" === typeof g.UNSAFE_componentWillMount && g.UNSAFE_componentWillMount()), "function" === typeof g.componentDidMount && (b.flags |= 4194308)) : ("function" === typeof g.componentDidMount && (b.flags |= 4194308), b.memoizedProps = d, b.memoizedState = k), g.props = d, g.state = k, g.context = l, d = h) : ("function" === typeof g.componentDidMount && (b.flags |= 4194308), d = false);
        } else {
          g = b.stateNode;
          lh(a, b);
          h = b.memoizedProps;
          l = b.type === b.elementType ? h : Ci(b.type, h);
          g.props = l;
          q = b.pendingProps;
          r = g.context;
          k = c.contextType;
          "object" === typeof k && null !== k ? k = eh(k) : (k = Zf(c) ? Xf : H.current, k = Yf(b, k));
          var y = c.getDerivedStateFromProps;
          (m = "function" === typeof y || "function" === typeof g.getSnapshotBeforeUpdate) || "function" !== typeof g.UNSAFE_componentWillReceiveProps && "function" !== typeof g.componentWillReceiveProps || (h !== q || r !== k) && Hi(b, g, d, k);
          jh = false;
          r = b.memoizedState;
          g.state = r;
          qh(b, d, g, e);
          var n = b.memoizedState;
          h !== q || r !== n || Wf.current || jh ? ("function" === typeof y && (Di(b, c, y, d), n = b.memoizedState), (l = jh || Fi(b, c, l, d, r, n, k) || false) ? (m || "function" !== typeof g.UNSAFE_componentWillUpdate && "function" !== typeof g.componentWillUpdate || ("function" === typeof g.componentWillUpdate && g.componentWillUpdate(d, n, k), "function" === typeof g.UNSAFE_componentWillUpdate && g.UNSAFE_componentWillUpdate(d, n, k)), "function" === typeof g.componentDidUpdate && (b.flags |= 4), "function" === typeof g.getSnapshotBeforeUpdate && (b.flags |= 1024)) : ("function" !== typeof g.componentDidUpdate || h === a.memoizedProps && r === a.memoizedState || (b.flags |= 4), "function" !== typeof g.getSnapshotBeforeUpdate || h === a.memoizedProps && r === a.memoizedState || (b.flags |= 1024), b.memoizedProps = d, b.memoizedState = n), g.props = d, g.state = n, g.context = k, d = l) : ("function" !== typeof g.componentDidUpdate || h === a.memoizedProps && r === a.memoizedState || (b.flags |= 4), "function" !== typeof g.getSnapshotBeforeUpdate || h === a.memoizedProps && r === a.memoizedState || (b.flags |= 1024), d = false);
        }
        return jj(a, b, c, d, f, e);
      }
      function jj(a, b, c, d, e, f) {
        gj(a, b);
        var g = 0 !== (b.flags & 128);
        if (!d && !g) return e && dg(b, c, false), Zi(a, b, f);
        d = b.stateNode;
        Wi.current = b;
        var h = g && "function" !== typeof c.getDerivedStateFromError ? null : d.render();
        b.flags |= 1;
        null !== a && g ? (b.child = Ug(b, a.child, null, f), b.child = Ug(b, null, h, f)) : Xi(a, b, h, f);
        b.memoizedState = d.state;
        e && dg(b, c, true);
        return b.child;
      }
      function kj(a) {
        var b = a.stateNode;
        b.pendingContext ? ag(a, b.pendingContext, b.pendingContext !== b.context) : b.context && ag(a, b.context, false);
        yh(a, b.containerInfo);
      }
      function lj(a, b, c, d, e) {
        Ig();
        Jg(e);
        b.flags |= 256;
        Xi(a, b, c, d);
        return b.child;
      }
      var mj = { dehydrated: null, treeContext: null, retryLane: 0 };
      function nj(a) {
        return { baseLanes: a, cachePool: null, transitions: null };
      }
      function oj(a, b, c) {
        var d = b.pendingProps, e = L.current, f = false, g = 0 !== (b.flags & 128), h;
        (h = g) || (h = null !== a && null === a.memoizedState ? false : 0 !== (e & 2));
        if (h) f = true, b.flags &= -129;
        else if (null === a || null !== a.memoizedState) e |= 1;
        G(L, e & 1);
        if (null === a) {
          Eg(b);
          a = b.memoizedState;
          if (null !== a && (a = a.dehydrated, null !== a)) return 0 === (b.mode & 1) ? b.lanes = 1 : "$!" === a.data ? b.lanes = 8 : b.lanes = 1073741824, null;
          g = d.children;
          a = d.fallback;
          return f ? (d = b.mode, f = b.child, g = { mode: "hidden", children: g }, 0 === (d & 1) && null !== f ? (f.childLanes = 0, f.pendingProps = g) : f = pj(g, d, 0, null), a = Tg(a, d, c, null), f.return = b, a.return = b, f.sibling = a, b.child = f, b.child.memoizedState = nj(c), b.memoizedState = mj, a) : qj(b, g);
        }
        e = a.memoizedState;
        if (null !== e && (h = e.dehydrated, null !== h)) return rj(a, b, g, d, h, e, c);
        if (f) {
          f = d.fallback;
          g = b.mode;
          e = a.child;
          h = e.sibling;
          var k = { mode: "hidden", children: d.children };
          0 === (g & 1) && b.child !== e ? (d = b.child, d.childLanes = 0, d.pendingProps = k, b.deletions = null) : (d = Pg(e, k), d.subtreeFlags = e.subtreeFlags & 14680064);
          null !== h ? f = Pg(h, f) : (f = Tg(f, g, c, null), f.flags |= 2);
          f.return = b;
          d.return = b;
          d.sibling = f;
          b.child = d;
          d = f;
          f = b.child;
          g = a.child.memoizedState;
          g = null === g ? nj(c) : { baseLanes: g.baseLanes | c, cachePool: null, transitions: g.transitions };
          f.memoizedState = g;
          f.childLanes = a.childLanes & ~c;
          b.memoizedState = mj;
          return d;
        }
        f = a.child;
        a = f.sibling;
        d = Pg(f, { mode: "visible", children: d.children });
        0 === (b.mode & 1) && (d.lanes = c);
        d.return = b;
        d.sibling = null;
        null !== a && (c = b.deletions, null === c ? (b.deletions = [a], b.flags |= 16) : c.push(a));
        b.child = d;
        b.memoizedState = null;
        return d;
      }
      function qj(a, b) {
        b = pj({ mode: "visible", children: b }, a.mode, 0, null);
        b.return = a;
        return a.child = b;
      }
      function sj(a, b, c, d) {
        null !== d && Jg(d);
        Ug(b, a.child, null, c);
        a = qj(b, b.pendingProps.children);
        a.flags |= 2;
        b.memoizedState = null;
        return a;
      }
      function rj(a, b, c, d, e, f, g) {
        if (c) {
          if (b.flags & 256) return b.flags &= -257, d = Ki(Error(p(422))), sj(a, b, g, d);
          if (null !== b.memoizedState) return b.child = a.child, b.flags |= 128, null;
          f = d.fallback;
          e = b.mode;
          d = pj({ mode: "visible", children: d.children }, e, 0, null);
          f = Tg(f, e, g, null);
          f.flags |= 2;
          d.return = b;
          f.return = b;
          d.sibling = f;
          b.child = d;
          0 !== (b.mode & 1) && Ug(b, a.child, null, g);
          b.child.memoizedState = nj(g);
          b.memoizedState = mj;
          return f;
        }
        if (0 === (b.mode & 1)) return sj(a, b, g, null);
        if ("$!" === e.data) {
          d = e.nextSibling && e.nextSibling.dataset;
          if (d) var h = d.dgst;
          d = h;
          f = Error(p(419));
          d = Ki(f, d, void 0);
          return sj(a, b, g, d);
        }
        h = 0 !== (g & a.childLanes);
        if (dh || h) {
          d = Q;
          if (null !== d) {
            switch (g & -g) {
              case 4:
                e = 2;
                break;
              case 16:
                e = 8;
                break;
              case 64:
              case 128:
              case 256:
              case 512:
              case 1024:
              case 2048:
              case 4096:
              case 8192:
              case 16384:
              case 32768:
              case 65536:
              case 131072:
              case 262144:
              case 524288:
              case 1048576:
              case 2097152:
              case 4194304:
              case 8388608:
              case 16777216:
              case 33554432:
              case 67108864:
                e = 32;
                break;
              case 536870912:
                e = 268435456;
                break;
              default:
                e = 0;
            }
            e = 0 !== (e & (d.suspendedLanes | g)) ? 0 : e;
            0 !== e && e !== f.retryLane && (f.retryLane = e, ih(a, e), gi(d, a, e, -1));
          }
          tj();
          d = Ki(Error(p(421)));
          return sj(a, b, g, d);
        }
        if ("$?" === e.data) return b.flags |= 128, b.child = a.child, b = uj.bind(null, a), e._reactRetry = b, null;
        a = f.treeContext;
        yg = Lf(e.nextSibling);
        xg = b;
        I = true;
        zg = null;
        null !== a && (og[pg++] = rg, og[pg++] = sg, og[pg++] = qg, rg = a.id, sg = a.overflow, qg = b);
        b = qj(b, d.children);
        b.flags |= 4096;
        return b;
      }
      function vj(a, b, c) {
        a.lanes |= b;
        var d = a.alternate;
        null !== d && (d.lanes |= b);
        bh(a.return, b, c);
      }
      function wj(a, b, c, d, e) {
        var f = a.memoizedState;
        null === f ? a.memoizedState = { isBackwards: b, rendering: null, renderingStartTime: 0, last: d, tail: c, tailMode: e } : (f.isBackwards = b, f.rendering = null, f.renderingStartTime = 0, f.last = d, f.tail = c, f.tailMode = e);
      }
      function xj(a, b, c) {
        var d = b.pendingProps, e = d.revealOrder, f = d.tail;
        Xi(a, b, d.children, c);
        d = L.current;
        if (0 !== (d & 2)) d = d & 1 | 2, b.flags |= 128;
        else {
          if (null !== a && 0 !== (a.flags & 128)) a: for (a = b.child; null !== a; ) {
            if (13 === a.tag) null !== a.memoizedState && vj(a, c, b);
            else if (19 === a.tag) vj(a, c, b);
            else if (null !== a.child) {
              a.child.return = a;
              a = a.child;
              continue;
            }
            if (a === b) break a;
            for (; null === a.sibling; ) {
              if (null === a.return || a.return === b) break a;
              a = a.return;
            }
            a.sibling.return = a.return;
            a = a.sibling;
          }
          d &= 1;
        }
        G(L, d);
        if (0 === (b.mode & 1)) b.memoizedState = null;
        else switch (e) {
          case "forwards":
            c = b.child;
            for (e = null; null !== c; ) a = c.alternate, null !== a && null === Ch(a) && (e = c), c = c.sibling;
            c = e;
            null === c ? (e = b.child, b.child = null) : (e = c.sibling, c.sibling = null);
            wj(b, false, e, c, f);
            break;
          case "backwards":
            c = null;
            e = b.child;
            for (b.child = null; null !== e; ) {
              a = e.alternate;
              if (null !== a && null === Ch(a)) {
                b.child = e;
                break;
              }
              a = e.sibling;
              e.sibling = c;
              c = e;
              e = a;
            }
            wj(b, true, c, null, f);
            break;
          case "together":
            wj(b, false, null, null, void 0);
            break;
          default:
            b.memoizedState = null;
        }
        return b.child;
      }
      function ij(a, b) {
        0 === (b.mode & 1) && null !== a && (a.alternate = null, b.alternate = null, b.flags |= 2);
      }
      function Zi(a, b, c) {
        null !== a && (b.dependencies = a.dependencies);
        rh |= b.lanes;
        if (0 === (c & b.childLanes)) return null;
        if (null !== a && b.child !== a.child) throw Error(p(153));
        if (null !== b.child) {
          a = b.child;
          c = Pg(a, a.pendingProps);
          b.child = c;
          for (c.return = b; null !== a.sibling; ) a = a.sibling, c = c.sibling = Pg(a, a.pendingProps), c.return = b;
          c.sibling = null;
        }
        return b.child;
      }
      function yj(a, b, c) {
        switch (b.tag) {
          case 3:
            kj(b);
            Ig();
            break;
          case 5:
            Ah(b);
            break;
          case 1:
            Zf(b.type) && cg(b);
            break;
          case 4:
            yh(b, b.stateNode.containerInfo);
            break;
          case 10:
            var d = b.type._context, e = b.memoizedProps.value;
            G(Wg, d._currentValue);
            d._currentValue = e;
            break;
          case 13:
            d = b.memoizedState;
            if (null !== d) {
              if (null !== d.dehydrated) return G(L, L.current & 1), b.flags |= 128, null;
              if (0 !== (c & b.child.childLanes)) return oj(a, b, c);
              G(L, L.current & 1);
              a = Zi(a, b, c);
              return null !== a ? a.sibling : null;
            }
            G(L, L.current & 1);
            break;
          case 19:
            d = 0 !== (c & b.childLanes);
            if (0 !== (a.flags & 128)) {
              if (d) return xj(a, b, c);
              b.flags |= 128;
            }
            e = b.memoizedState;
            null !== e && (e.rendering = null, e.tail = null, e.lastEffect = null);
            G(L, L.current);
            if (d) break;
            else return null;
          case 22:
          case 23:
            return b.lanes = 0, dj(a, b, c);
        }
        return Zi(a, b, c);
      }
      var zj;
      var Aj;
      var Bj;
      var Cj;
      zj = function(a, b) {
        for (var c = b.child; null !== c; ) {
          if (5 === c.tag || 6 === c.tag) a.appendChild(c.stateNode);
          else if (4 !== c.tag && null !== c.child) {
            c.child.return = c;
            c = c.child;
            continue;
          }
          if (c === b) break;
          for (; null === c.sibling; ) {
            if (null === c.return || c.return === b) return;
            c = c.return;
          }
          c.sibling.return = c.return;
          c = c.sibling;
        }
      };
      Aj = function() {
      };
      Bj = function(a, b, c, d) {
        var e = a.memoizedProps;
        if (e !== d) {
          a = b.stateNode;
          xh(uh.current);
          var f = null;
          switch (c) {
            case "input":
              e = Ya(a, e);
              d = Ya(a, d);
              f = [];
              break;
            case "select":
              e = A({}, e, { value: void 0 });
              d = A({}, d, { value: void 0 });
              f = [];
              break;
            case "textarea":
              e = gb(a, e);
              d = gb(a, d);
              f = [];
              break;
            default:
              "function" !== typeof e.onClick && "function" === typeof d.onClick && (a.onclick = Bf);
          }
          ub(c, d);
          var g;
          c = null;
          for (l in e) if (!d.hasOwnProperty(l) && e.hasOwnProperty(l) && null != e[l]) if ("style" === l) {
            var h = e[l];
            for (g in h) h.hasOwnProperty(g) && (c || (c = {}), c[g] = "");
          } else "dangerouslySetInnerHTML" !== l && "children" !== l && "suppressContentEditableWarning" !== l && "suppressHydrationWarning" !== l && "autoFocus" !== l && (ea.hasOwnProperty(l) ? f || (f = []) : (f = f || []).push(l, null));
          for (l in d) {
            var k = d[l];
            h = null != e ? e[l] : void 0;
            if (d.hasOwnProperty(l) && k !== h && (null != k || null != h)) if ("style" === l) if (h) {
              for (g in h) !h.hasOwnProperty(g) || k && k.hasOwnProperty(g) || (c || (c = {}), c[g] = "");
              for (g in k) k.hasOwnProperty(g) && h[g] !== k[g] && (c || (c = {}), c[g] = k[g]);
            } else c || (f || (f = []), f.push(
              l,
              c
            )), c = k;
            else "dangerouslySetInnerHTML" === l ? (k = k ? k.__html : void 0, h = h ? h.__html : void 0, null != k && h !== k && (f = f || []).push(l, k)) : "children" === l ? "string" !== typeof k && "number" !== typeof k || (f = f || []).push(l, "" + k) : "suppressContentEditableWarning" !== l && "suppressHydrationWarning" !== l && (ea.hasOwnProperty(l) ? (null != k && "onScroll" === l && D("scroll", a), f || h === k || (f = [])) : (f = f || []).push(l, k));
          }
          c && (f = f || []).push("style", c);
          var l = f;
          if (b.updateQueue = l) b.flags |= 4;
        }
      };
      Cj = function(a, b, c, d) {
        c !== d && (b.flags |= 4);
      };
      function Dj(a, b) {
        if (!I) switch (a.tailMode) {
          case "hidden":
            b = a.tail;
            for (var c = null; null !== b; ) null !== b.alternate && (c = b), b = b.sibling;
            null === c ? a.tail = null : c.sibling = null;
            break;
          case "collapsed":
            c = a.tail;
            for (var d = null; null !== c; ) null !== c.alternate && (d = c), c = c.sibling;
            null === d ? b || null === a.tail ? a.tail = null : a.tail.sibling = null : d.sibling = null;
        }
      }
      function S(a) {
        var b = null !== a.alternate && a.alternate.child === a.child, c = 0, d = 0;
        if (b) for (var e = a.child; null !== e; ) c |= e.lanes | e.childLanes, d |= e.subtreeFlags & 14680064, d |= e.flags & 14680064, e.return = a, e = e.sibling;
        else for (e = a.child; null !== e; ) c |= e.lanes | e.childLanes, d |= e.subtreeFlags, d |= e.flags, e.return = a, e = e.sibling;
        a.subtreeFlags |= d;
        a.childLanes = c;
        return b;
      }
      function Ej(a, b, c) {
        var d = b.pendingProps;
        wg(b);
        switch (b.tag) {
          case 2:
          case 16:
          case 15:
          case 0:
          case 11:
          case 7:
          case 8:
          case 12:
          case 9:
          case 14:
            return S(b), null;
          case 1:
            return Zf(b.type) && $f(), S(b), null;
          case 3:
            d = b.stateNode;
            zh();
            E(Wf);
            E(H);
            Eh();
            d.pendingContext && (d.context = d.pendingContext, d.pendingContext = null);
            if (null === a || null === a.child) Gg(b) ? b.flags |= 4 : null === a || a.memoizedState.isDehydrated && 0 === (b.flags & 256) || (b.flags |= 1024, null !== zg && (Fj(zg), zg = null));
            Aj(a, b);
            S(b);
            return null;
          case 5:
            Bh(b);
            var e = xh(wh.current);
            c = b.type;
            if (null !== a && null != b.stateNode) Bj(a, b, c, d, e), a.ref !== b.ref && (b.flags |= 512, b.flags |= 2097152);
            else {
              if (!d) {
                if (null === b.stateNode) throw Error(p(166));
                S(b);
                return null;
              }
              a = xh(uh.current);
              if (Gg(b)) {
                d = b.stateNode;
                c = b.type;
                var f = b.memoizedProps;
                d[Of] = b;
                d[Pf] = f;
                a = 0 !== (b.mode & 1);
                switch (c) {
                  case "dialog":
                    D("cancel", d);
                    D("close", d);
                    break;
                  case "iframe":
                  case "object":
                  case "embed":
                    D("load", d);
                    break;
                  case "video":
                  case "audio":
                    for (e = 0; e < lf.length; e++) D(lf[e], d);
                    break;
                  case "source":
                    D("error", d);
                    break;
                  case "img":
                  case "image":
                  case "link":
                    D(
                      "error",
                      d
                    );
                    D("load", d);
                    break;
                  case "details":
                    D("toggle", d);
                    break;
                  case "input":
                    Za(d, f);
                    D("invalid", d);
                    break;
                  case "select":
                    d._wrapperState = { wasMultiple: !!f.multiple };
                    D("invalid", d);
                    break;
                  case "textarea":
                    hb(d, f), D("invalid", d);
                }
                ub(c, f);
                e = null;
                for (var g in f) if (f.hasOwnProperty(g)) {
                  var h = f[g];
                  "children" === g ? "string" === typeof h ? d.textContent !== h && (true !== f.suppressHydrationWarning && Af(d.textContent, h, a), e = ["children", h]) : "number" === typeof h && d.textContent !== "" + h && (true !== f.suppressHydrationWarning && Af(
                    d.textContent,
                    h,
                    a
                  ), e = ["children", "" + h]) : ea.hasOwnProperty(g) && null != h && "onScroll" === g && D("scroll", d);
                }
                switch (c) {
                  case "input":
                    Va(d);
                    db(d, f, true);
                    break;
                  case "textarea":
                    Va(d);
                    jb(d);
                    break;
                  case "select":
                  case "option":
                    break;
                  default:
                    "function" === typeof f.onClick && (d.onclick = Bf);
                }
                d = e;
                b.updateQueue = d;
                null !== d && (b.flags |= 4);
              } else {
                g = 9 === e.nodeType ? e : e.ownerDocument;
                "http://www.w3.org/1999/xhtml" === a && (a = kb(c));
                "http://www.w3.org/1999/xhtml" === a ? "script" === c ? (a = g.createElement("div"), a.innerHTML = "<script><\/script>", a = a.removeChild(a.firstChild)) : "string" === typeof d.is ? a = g.createElement(c, { is: d.is }) : (a = g.createElement(c), "select" === c && (g = a, d.multiple ? g.multiple = true : d.size && (g.size = d.size))) : a = g.createElementNS(a, c);
                a[Of] = b;
                a[Pf] = d;
                zj(a, b, false, false);
                b.stateNode = a;
                a: {
                  g = vb(c, d);
                  switch (c) {
                    case "dialog":
                      D("cancel", a);
                      D("close", a);
                      e = d;
                      break;
                    case "iframe":
                    case "object":
                    case "embed":
                      D("load", a);
                      e = d;
                      break;
                    case "video":
                    case "audio":
                      for (e = 0; e < lf.length; e++) D(lf[e], a);
                      e = d;
                      break;
                    case "source":
                      D("error", a);
                      e = d;
                      break;
                    case "img":
                    case "image":
                    case "link":
                      D(
                        "error",
                        a
                      );
                      D("load", a);
                      e = d;
                      break;
                    case "details":
                      D("toggle", a);
                      e = d;
                      break;
                    case "input":
                      Za(a, d);
                      e = Ya(a, d);
                      D("invalid", a);
                      break;
                    case "option":
                      e = d;
                      break;
                    case "select":
                      a._wrapperState = { wasMultiple: !!d.multiple };
                      e = A({}, d, { value: void 0 });
                      D("invalid", a);
                      break;
                    case "textarea":
                      hb(a, d);
                      e = gb(a, d);
                      D("invalid", a);
                      break;
                    default:
                      e = d;
                  }
                  ub(c, e);
                  h = e;
                  for (f in h) if (h.hasOwnProperty(f)) {
                    var k = h[f];
                    "style" === f ? sb(a, k) : "dangerouslySetInnerHTML" === f ? (k = k ? k.__html : void 0, null != k && nb(a, k)) : "children" === f ? "string" === typeof k ? ("textarea" !== c || "" !== k) && ob(a, k) : "number" === typeof k && ob(a, "" + k) : "suppressContentEditableWarning" !== f && "suppressHydrationWarning" !== f && "autoFocus" !== f && (ea.hasOwnProperty(f) ? null != k && "onScroll" === f && D("scroll", a) : null != k && ta(a, f, k, g));
                  }
                  switch (c) {
                    case "input":
                      Va(a);
                      db(a, d, false);
                      break;
                    case "textarea":
                      Va(a);
                      jb(a);
                      break;
                    case "option":
                      null != d.value && a.setAttribute("value", "" + Sa(d.value));
                      break;
                    case "select":
                      a.multiple = !!d.multiple;
                      f = d.value;
                      null != f ? fb(a, !!d.multiple, f, false) : null != d.defaultValue && fb(
                        a,
                        !!d.multiple,
                        d.defaultValue,
                        true
                      );
                      break;
                    default:
                      "function" === typeof e.onClick && (a.onclick = Bf);
                  }
                  switch (c) {
                    case "button":
                    case "input":
                    case "select":
                    case "textarea":
                      d = !!d.autoFocus;
                      break a;
                    case "img":
                      d = true;
                      break a;
                    default:
                      d = false;
                  }
                }
                d && (b.flags |= 4);
              }
              null !== b.ref && (b.flags |= 512, b.flags |= 2097152);
            }
            S(b);
            return null;
          case 6:
            if (a && null != b.stateNode) Cj(a, b, a.memoizedProps, d);
            else {
              if ("string" !== typeof d && null === b.stateNode) throw Error(p(166));
              c = xh(wh.current);
              xh(uh.current);
              if (Gg(b)) {
                d = b.stateNode;
                c = b.memoizedProps;
                d[Of] = b;
                if (f = d.nodeValue !== c) {
                  if (a = xg, null !== a) switch (a.tag) {
                    case 3:
                      Af(d.nodeValue, c, 0 !== (a.mode & 1));
                      break;
                    case 5:
                      true !== a.memoizedProps.suppressHydrationWarning && Af(d.nodeValue, c, 0 !== (a.mode & 1));
                  }
                }
                f && (b.flags |= 4);
              } else d = (9 === c.nodeType ? c : c.ownerDocument).createTextNode(d), d[Of] = b, b.stateNode = d;
            }
            S(b);
            return null;
          case 13:
            E(L);
            d = b.memoizedState;
            if (null === a || null !== a.memoizedState && null !== a.memoizedState.dehydrated) {
              if (I && null !== yg && 0 !== (b.mode & 1) && 0 === (b.flags & 128)) Hg(), Ig(), b.flags |= 98560, f = false;
              else if (f = Gg(b), null !== d && null !== d.dehydrated) {
                if (null === a) {
                  if (!f) throw Error(p(318));
                  f = b.memoizedState;
                  f = null !== f ? f.dehydrated : null;
                  if (!f) throw Error(p(317));
                  f[Of] = b;
                } else Ig(), 0 === (b.flags & 128) && (b.memoizedState = null), b.flags |= 4;
                S(b);
                f = false;
              } else null !== zg && (Fj(zg), zg = null), f = true;
              if (!f) return b.flags & 65536 ? b : null;
            }
            if (0 !== (b.flags & 128)) return b.lanes = c, b;
            d = null !== d;
            d !== (null !== a && null !== a.memoizedState) && d && (b.child.flags |= 8192, 0 !== (b.mode & 1) && (null === a || 0 !== (L.current & 1) ? 0 === T && (T = 3) : tj()));
            null !== b.updateQueue && (b.flags |= 4);
            S(b);
            return null;
          case 4:
            return zh(), Aj(a, b), null === a && sf(b.stateNode.containerInfo), S(b), null;
          case 10:
            return ah(b.type._context), S(b), null;
          case 17:
            return Zf(b.type) && $f(), S(b), null;
          case 19:
            E(L);
            f = b.memoizedState;
            if (null === f) return S(b), null;
            d = 0 !== (b.flags & 128);
            g = f.rendering;
            if (null === g) if (d) Dj(f, false);
            else {
              if (0 !== T || null !== a && 0 !== (a.flags & 128)) for (a = b.child; null !== a; ) {
                g = Ch(a);
                if (null !== g) {
                  b.flags |= 128;
                  Dj(f, false);
                  d = g.updateQueue;
                  null !== d && (b.updateQueue = d, b.flags |= 4);
                  b.subtreeFlags = 0;
                  d = c;
                  for (c = b.child; null !== c; ) f = c, a = d, f.flags &= 14680066, g = f.alternate, null === g ? (f.childLanes = 0, f.lanes = a, f.child = null, f.subtreeFlags = 0, f.memoizedProps = null, f.memoizedState = null, f.updateQueue = null, f.dependencies = null, f.stateNode = null) : (f.childLanes = g.childLanes, f.lanes = g.lanes, f.child = g.child, f.subtreeFlags = 0, f.deletions = null, f.memoizedProps = g.memoizedProps, f.memoizedState = g.memoizedState, f.updateQueue = g.updateQueue, f.type = g.type, a = g.dependencies, f.dependencies = null === a ? null : { lanes: a.lanes, firstContext: a.firstContext }), c = c.sibling;
                  G(L, L.current & 1 | 2);
                  return b.child;
                }
                a = a.sibling;
              }
              null !== f.tail && B() > Gj && (b.flags |= 128, d = true, Dj(f, false), b.lanes = 4194304);
            }
            else {
              if (!d) if (a = Ch(g), null !== a) {
                if (b.flags |= 128, d = true, c = a.updateQueue, null !== c && (b.updateQueue = c, b.flags |= 4), Dj(f, true), null === f.tail && "hidden" === f.tailMode && !g.alternate && !I) return S(b), null;
              } else 2 * B() - f.renderingStartTime > Gj && 1073741824 !== c && (b.flags |= 128, d = true, Dj(f, false), b.lanes = 4194304);
              f.isBackwards ? (g.sibling = b.child, b.child = g) : (c = f.last, null !== c ? c.sibling = g : b.child = g, f.last = g);
            }
            if (null !== f.tail) return b = f.tail, f.rendering = b, f.tail = b.sibling, f.renderingStartTime = B(), b.sibling = null, c = L.current, G(L, d ? c & 1 | 2 : c & 1), b;
            S(b);
            return null;
          case 22:
          case 23:
            return Hj(), d = null !== b.memoizedState, null !== a && null !== a.memoizedState !== d && (b.flags |= 8192), d && 0 !== (b.mode & 1) ? 0 !== (fj & 1073741824) && (S(b), b.subtreeFlags & 6 && (b.flags |= 8192)) : S(b), null;
          case 24:
            return null;
          case 25:
            return null;
        }
        throw Error(p(156, b.tag));
      }
      function Ij(a, b) {
        wg(b);
        switch (b.tag) {
          case 1:
            return Zf(b.type) && $f(), a = b.flags, a & 65536 ? (b.flags = a & -65537 | 128, b) : null;
          case 3:
            return zh(), E(Wf), E(H), Eh(), a = b.flags, 0 !== (a & 65536) && 0 === (a & 128) ? (b.flags = a & -65537 | 128, b) : null;
          case 5:
            return Bh(b), null;
          case 13:
            E(L);
            a = b.memoizedState;
            if (null !== a && null !== a.dehydrated) {
              if (null === b.alternate) throw Error(p(340));
              Ig();
            }
            a = b.flags;
            return a & 65536 ? (b.flags = a & -65537 | 128, b) : null;
          case 19:
            return E(L), null;
          case 4:
            return zh(), null;
          case 10:
            return ah(b.type._context), null;
          case 22:
          case 23:
            return Hj(), null;
          case 24:
            return null;
          default:
            return null;
        }
      }
      var Jj = false;
      var U = false;
      var Kj = "function" === typeof WeakSet ? WeakSet : Set;
      var V = null;
      function Lj(a, b) {
        var c = a.ref;
        if (null !== c) if ("function" === typeof c) try {
          c(null);
        } catch (d) {
          W(a, b, d);
        }
        else c.current = null;
      }
      function Mj(a, b, c) {
        try {
          c();
        } catch (d) {
          W(a, b, d);
        }
      }
      var Nj = false;
      function Oj(a, b) {
        Cf = dd;
        a = Me();
        if (Ne(a)) {
          if ("selectionStart" in a) var c = { start: a.selectionStart, end: a.selectionEnd };
          else a: {
            c = (c = a.ownerDocument) && c.defaultView || window;
            var d = c.getSelection && c.getSelection();
            if (d && 0 !== d.rangeCount) {
              c = d.anchorNode;
              var e = d.anchorOffset, f = d.focusNode;
              d = d.focusOffset;
              try {
                c.nodeType, f.nodeType;
              } catch (F) {
                c = null;
                break a;
              }
              var g = 0, h = -1, k = -1, l = 0, m = 0, q = a, r = null;
              b: for (; ; ) {
                for (var y; ; ) {
                  q !== c || 0 !== e && 3 !== q.nodeType || (h = g + e);
                  q !== f || 0 !== d && 3 !== q.nodeType || (k = g + d);
                  3 === q.nodeType && (g += q.nodeValue.length);
                  if (null === (y = q.firstChild)) break;
                  r = q;
                  q = y;
                }
                for (; ; ) {
                  if (q === a) break b;
                  r === c && ++l === e && (h = g);
                  r === f && ++m === d && (k = g);
                  if (null !== (y = q.nextSibling)) break;
                  q = r;
                  r = q.parentNode;
                }
                q = y;
              }
              c = -1 === h || -1 === k ? null : { start: h, end: k };
            } else c = null;
          }
          c = c || { start: 0, end: 0 };
        } else c = null;
        Df = { focusedElem: a, selectionRange: c };
        dd = false;
        for (V = b; null !== V; ) if (b = V, a = b.child, 0 !== (b.subtreeFlags & 1028) && null !== a) a.return = b, V = a;
        else for (; null !== V; ) {
          b = V;
          try {
            var n = b.alternate;
            if (0 !== (b.flags & 1024)) switch (b.tag) {
              case 0:
              case 11:
              case 15:
                break;
              case 1:
                if (null !== n) {
                  var t = n.memoizedProps, J = n.memoizedState, x = b.stateNode, w = x.getSnapshotBeforeUpdate(b.elementType === b.type ? t : Ci(b.type, t), J);
                  x.__reactInternalSnapshotBeforeUpdate = w;
                }
                break;
              case 3:
                var u = b.stateNode.containerInfo;
                1 === u.nodeType ? u.textContent = "" : 9 === u.nodeType && u.documentElement && u.removeChild(u.documentElement);
                break;
              case 5:
              case 6:
              case 4:
              case 17:
                break;
              default:
                throw Error(p(163));
            }
          } catch (F) {
            W(b, b.return, F);
          }
          a = b.sibling;
          if (null !== a) {
            a.return = b.return;
            V = a;
            break;
          }
          V = b.return;
        }
        n = Nj;
        Nj = false;
        return n;
      }
      function Pj(a, b, c) {
        var d = b.updateQueue;
        d = null !== d ? d.lastEffect : null;
        if (null !== d) {
          var e = d = d.next;
          do {
            if ((e.tag & a) === a) {
              var f = e.destroy;
              e.destroy = void 0;
              void 0 !== f && Mj(b, c, f);
            }
            e = e.next;
          } while (e !== d);
        }
      }
      function Qj(a, b) {
        b = b.updateQueue;
        b = null !== b ? b.lastEffect : null;
        if (null !== b) {
          var c = b = b.next;
          do {
            if ((c.tag & a) === a) {
              var d = c.create;
              c.destroy = d();
            }
            c = c.next;
          } while (c !== b);
        }
      }
      function Rj(a) {
        var b = a.ref;
        if (null !== b) {
          var c = a.stateNode;
          switch (a.tag) {
            case 5:
              a = c;
              break;
            default:
              a = c;
          }
          "function" === typeof b ? b(a) : b.current = a;
        }
      }
      function Sj(a) {
        var b = a.alternate;
        null !== b && (a.alternate = null, Sj(b));
        a.child = null;
        a.deletions = null;
        a.sibling = null;
        5 === a.tag && (b = a.stateNode, null !== b && (delete b[Of], delete b[Pf], delete b[of], delete b[Qf], delete b[Rf]));
        a.stateNode = null;
        a.return = null;
        a.dependencies = null;
        a.memoizedProps = null;
        a.memoizedState = null;
        a.pendingProps = null;
        a.stateNode = null;
        a.updateQueue = null;
      }
      function Tj(a) {
        return 5 === a.tag || 3 === a.tag || 4 === a.tag;
      }
      function Uj(a) {
        a: for (; ; ) {
          for (; null === a.sibling; ) {
            if (null === a.return || Tj(a.return)) return null;
            a = a.return;
          }
          a.sibling.return = a.return;
          for (a = a.sibling; 5 !== a.tag && 6 !== a.tag && 18 !== a.tag; ) {
            if (a.flags & 2) continue a;
            if (null === a.child || 4 === a.tag) continue a;
            else a.child.return = a, a = a.child;
          }
          if (!(a.flags & 2)) return a.stateNode;
        }
      }
      function Vj(a, b, c) {
        var d = a.tag;
        if (5 === d || 6 === d) a = a.stateNode, b ? 8 === c.nodeType ? c.parentNode.insertBefore(a, b) : c.insertBefore(a, b) : (8 === c.nodeType ? (b = c.parentNode, b.insertBefore(a, c)) : (b = c, b.appendChild(a)), c = c._reactRootContainer, null !== c && void 0 !== c || null !== b.onclick || (b.onclick = Bf));
        else if (4 !== d && (a = a.child, null !== a)) for (Vj(a, b, c), a = a.sibling; null !== a; ) Vj(a, b, c), a = a.sibling;
      }
      function Wj(a, b, c) {
        var d = a.tag;
        if (5 === d || 6 === d) a = a.stateNode, b ? c.insertBefore(a, b) : c.appendChild(a);
        else if (4 !== d && (a = a.child, null !== a)) for (Wj(a, b, c), a = a.sibling; null !== a; ) Wj(a, b, c), a = a.sibling;
      }
      var X = null;
      var Xj = false;
      function Yj(a, b, c) {
        for (c = c.child; null !== c; ) Zj(a, b, c), c = c.sibling;
      }
      function Zj(a, b, c) {
        if (lc && "function" === typeof lc.onCommitFiberUnmount) try {
          lc.onCommitFiberUnmount(kc, c);
        } catch (h) {
        }
        switch (c.tag) {
          case 5:
            U || Lj(c, b);
          case 6:
            var d = X, e = Xj;
            X = null;
            Yj(a, b, c);
            X = d;
            Xj = e;
            null !== X && (Xj ? (a = X, c = c.stateNode, 8 === a.nodeType ? a.parentNode.removeChild(c) : a.removeChild(c)) : X.removeChild(c.stateNode));
            break;
          case 18:
            null !== X && (Xj ? (a = X, c = c.stateNode, 8 === a.nodeType ? Kf(a.parentNode, c) : 1 === a.nodeType && Kf(a, c), bd(a)) : Kf(X, c.stateNode));
            break;
          case 4:
            d = X;
            e = Xj;
            X = c.stateNode.containerInfo;
            Xj = true;
            Yj(a, b, c);
            X = d;
            Xj = e;
            break;
          case 0:
          case 11:
          case 14:
          case 15:
            if (!U && (d = c.updateQueue, null !== d && (d = d.lastEffect, null !== d))) {
              e = d = d.next;
              do {
                var f = e, g = f.destroy;
                f = f.tag;
                void 0 !== g && (0 !== (f & 2) ? Mj(c, b, g) : 0 !== (f & 4) && Mj(c, b, g));
                e = e.next;
              } while (e !== d);
            }
            Yj(a, b, c);
            break;
          case 1:
            if (!U && (Lj(c, b), d = c.stateNode, "function" === typeof d.componentWillUnmount)) try {
              d.props = c.memoizedProps, d.state = c.memoizedState, d.componentWillUnmount();
            } catch (h) {
              W(c, b, h);
            }
            Yj(a, b, c);
            break;
          case 21:
            Yj(a, b, c);
            break;
          case 22:
            c.mode & 1 ? (U = (d = U) || null !== c.memoizedState, Yj(a, b, c), U = d) : Yj(a, b, c);
            break;
          default:
            Yj(a, b, c);
        }
      }
      function ak(a) {
        var b = a.updateQueue;
        if (null !== b) {
          a.updateQueue = null;
          var c = a.stateNode;
          null === c && (c = a.stateNode = new Kj());
          b.forEach(function(b2) {
            var d = bk.bind(null, a, b2);
            c.has(b2) || (c.add(b2), b2.then(d, d));
          });
        }
      }
      function ck(a, b) {
        var c = b.deletions;
        if (null !== c) for (var d = 0; d < c.length; d++) {
          var e = c[d];
          try {
            var f = a, g = b, h = g;
            a: for (; null !== h; ) {
              switch (h.tag) {
                case 5:
                  X = h.stateNode;
                  Xj = false;
                  break a;
                case 3:
                  X = h.stateNode.containerInfo;
                  Xj = true;
                  break a;
                case 4:
                  X = h.stateNode.containerInfo;
                  Xj = true;
                  break a;
              }
              h = h.return;
            }
            if (null === X) throw Error(p(160));
            Zj(f, g, e);
            X = null;
            Xj = false;
            var k = e.alternate;
            null !== k && (k.return = null);
            e.return = null;
          } catch (l) {
            W(e, b, l);
          }
        }
        if (b.subtreeFlags & 12854) for (b = b.child; null !== b; ) dk(b, a), b = b.sibling;
      }
      function dk(a, b) {
        var c = a.alternate, d = a.flags;
        switch (a.tag) {
          case 0:
          case 11:
          case 14:
          case 15:
            ck(b, a);
            ek(a);
            if (d & 4) {
              try {
                Pj(3, a, a.return), Qj(3, a);
              } catch (t) {
                W(a, a.return, t);
              }
              try {
                Pj(5, a, a.return);
              } catch (t) {
                W(a, a.return, t);
              }
            }
            break;
          case 1:
            ck(b, a);
            ek(a);
            d & 512 && null !== c && Lj(c, c.return);
            break;
          case 5:
            ck(b, a);
            ek(a);
            d & 512 && null !== c && Lj(c, c.return);
            if (a.flags & 32) {
              var e = a.stateNode;
              try {
                ob(e, "");
              } catch (t) {
                W(a, a.return, t);
              }
            }
            if (d & 4 && (e = a.stateNode, null != e)) {
              var f = a.memoizedProps, g = null !== c ? c.memoizedProps : f, h = a.type, k = a.updateQueue;
              a.updateQueue = null;
              if (null !== k) try {
                "input" === h && "radio" === f.type && null != f.name && ab(e, f);
                vb(h, g);
                var l = vb(h, f);
                for (g = 0; g < k.length; g += 2) {
                  var m = k[g], q = k[g + 1];
                  "style" === m ? sb(e, q) : "dangerouslySetInnerHTML" === m ? nb(e, q) : "children" === m ? ob(e, q) : ta(e, m, q, l);
                }
                switch (h) {
                  case "input":
                    bb(e, f);
                    break;
                  case "textarea":
                    ib(e, f);
                    break;
                  case "select":
                    var r = e._wrapperState.wasMultiple;
                    e._wrapperState.wasMultiple = !!f.multiple;
                    var y = f.value;
                    null != y ? fb(e, !!f.multiple, y, false) : r !== !!f.multiple && (null != f.defaultValue ? fb(
                      e,
                      !!f.multiple,
                      f.defaultValue,
                      true
                    ) : fb(e, !!f.multiple, f.multiple ? [] : "", false));
                }
                e[Pf] = f;
              } catch (t) {
                W(a, a.return, t);
              }
            }
            break;
          case 6:
            ck(b, a);
            ek(a);
            if (d & 4) {
              if (null === a.stateNode) throw Error(p(162));
              e = a.stateNode;
              f = a.memoizedProps;
              try {
                e.nodeValue = f;
              } catch (t) {
                W(a, a.return, t);
              }
            }
            break;
          case 3:
            ck(b, a);
            ek(a);
            if (d & 4 && null !== c && c.memoizedState.isDehydrated) try {
              bd(b.containerInfo);
            } catch (t) {
              W(a, a.return, t);
            }
            break;
          case 4:
            ck(b, a);
            ek(a);
            break;
          case 13:
            ck(b, a);
            ek(a);
            e = a.child;
            e.flags & 8192 && (f = null !== e.memoizedState, e.stateNode.isHidden = f, !f || null !== e.alternate && null !== e.alternate.memoizedState || (fk = B()));
            d & 4 && ak(a);
            break;
          case 22:
            m = null !== c && null !== c.memoizedState;
            a.mode & 1 ? (U = (l = U) || m, ck(b, a), U = l) : ck(b, a);
            ek(a);
            if (d & 8192) {
              l = null !== a.memoizedState;
              if ((a.stateNode.isHidden = l) && !m && 0 !== (a.mode & 1)) for (V = a, m = a.child; null !== m; ) {
                for (q = V = m; null !== V; ) {
                  r = V;
                  y = r.child;
                  switch (r.tag) {
                    case 0:
                    case 11:
                    case 14:
                    case 15:
                      Pj(4, r, r.return);
                      break;
                    case 1:
                      Lj(r, r.return);
                      var n = r.stateNode;
                      if ("function" === typeof n.componentWillUnmount) {
                        d = r;
                        c = r.return;
                        try {
                          b = d, n.props = b.memoizedProps, n.state = b.memoizedState, n.componentWillUnmount();
                        } catch (t) {
                          W(d, c, t);
                        }
                      }
                      break;
                    case 5:
                      Lj(r, r.return);
                      break;
                    case 22:
                      if (null !== r.memoizedState) {
                        gk(q);
                        continue;
                      }
                  }
                  null !== y ? (y.return = r, V = y) : gk(q);
                }
                m = m.sibling;
              }
              a: for (m = null, q = a; ; ) {
                if (5 === q.tag) {
                  if (null === m) {
                    m = q;
                    try {
                      e = q.stateNode, l ? (f = e.style, "function" === typeof f.setProperty ? f.setProperty("display", "none", "important") : f.display = "none") : (h = q.stateNode, k = q.memoizedProps.style, g = void 0 !== k && null !== k && k.hasOwnProperty("display") ? k.display : null, h.style.display = rb("display", g));
                    } catch (t) {
                      W(a, a.return, t);
                    }
                  }
                } else if (6 === q.tag) {
                  if (null === m) try {
                    q.stateNode.nodeValue = l ? "" : q.memoizedProps;
                  } catch (t) {
                    W(a, a.return, t);
                  }
                } else if ((22 !== q.tag && 23 !== q.tag || null === q.memoizedState || q === a) && null !== q.child) {
                  q.child.return = q;
                  q = q.child;
                  continue;
                }
                if (q === a) break a;
                for (; null === q.sibling; ) {
                  if (null === q.return || q.return === a) break a;
                  m === q && (m = null);
                  q = q.return;
                }
                m === q && (m = null);
                q.sibling.return = q.return;
                q = q.sibling;
              }
            }
            break;
          case 19:
            ck(b, a);
            ek(a);
            d & 4 && ak(a);
            break;
          case 21:
            break;
          default:
            ck(
              b,
              a
            ), ek(a);
        }
      }
      function ek(a) {
        var b = a.flags;
        if (b & 2) {
          try {
            a: {
              for (var c = a.return; null !== c; ) {
                if (Tj(c)) {
                  var d = c;
                  break a;
                }
                c = c.return;
              }
              throw Error(p(160));
            }
            switch (d.tag) {
              case 5:
                var e = d.stateNode;
                d.flags & 32 && (ob(e, ""), d.flags &= -33);
                var f = Uj(a);
                Wj(a, f, e);
                break;
              case 3:
              case 4:
                var g = d.stateNode.containerInfo, h = Uj(a);
                Vj(a, h, g);
                break;
              default:
                throw Error(p(161));
            }
          } catch (k) {
            W(a, a.return, k);
          }
          a.flags &= -3;
        }
        b & 4096 && (a.flags &= -4097);
      }
      function hk(a, b, c) {
        V = a;
        ik(a, b, c);
      }
      function ik(a, b, c) {
        for (var d = 0 !== (a.mode & 1); null !== V; ) {
          var e = V, f = e.child;
          if (22 === e.tag && d) {
            var g = null !== e.memoizedState || Jj;
            if (!g) {
              var h = e.alternate, k = null !== h && null !== h.memoizedState || U;
              h = Jj;
              var l = U;
              Jj = g;
              if ((U = k) && !l) for (V = e; null !== V; ) g = V, k = g.child, 22 === g.tag && null !== g.memoizedState ? jk(e) : null !== k ? (k.return = g, V = k) : jk(e);
              for (; null !== f; ) V = f, ik(f, b, c), f = f.sibling;
              V = e;
              Jj = h;
              U = l;
            }
            kk(a, b, c);
          } else 0 !== (e.subtreeFlags & 8772) && null !== f ? (f.return = e, V = f) : kk(a, b, c);
        }
      }
      function kk(a) {
        for (; null !== V; ) {
          var b = V;
          if (0 !== (b.flags & 8772)) {
            var c = b.alternate;
            try {
              if (0 !== (b.flags & 8772)) switch (b.tag) {
                case 0:
                case 11:
                case 15:
                  U || Qj(5, b);
                  break;
                case 1:
                  var d = b.stateNode;
                  if (b.flags & 4 && !U) if (null === c) d.componentDidMount();
                  else {
                    var e = b.elementType === b.type ? c.memoizedProps : Ci(b.type, c.memoizedProps);
                    d.componentDidUpdate(e, c.memoizedState, d.__reactInternalSnapshotBeforeUpdate);
                  }
                  var f = b.updateQueue;
                  null !== f && sh(b, f, d);
                  break;
                case 3:
                  var g = b.updateQueue;
                  if (null !== g) {
                    c = null;
                    if (null !== b.child) switch (b.child.tag) {
                      case 5:
                        c = b.child.stateNode;
                        break;
                      case 1:
                        c = b.child.stateNode;
                    }
                    sh(b, g, c);
                  }
                  break;
                case 5:
                  var h = b.stateNode;
                  if (null === c && b.flags & 4) {
                    c = h;
                    var k = b.memoizedProps;
                    switch (b.type) {
                      case "button":
                      case "input":
                      case "select":
                      case "textarea":
                        k.autoFocus && c.focus();
                        break;
                      case "img":
                        k.src && (c.src = k.src);
                    }
                  }
                  break;
                case 6:
                  break;
                case 4:
                  break;
                case 12:
                  break;
                case 13:
                  if (null === b.memoizedState) {
                    var l = b.alternate;
                    if (null !== l) {
                      var m = l.memoizedState;
                      if (null !== m) {
                        var q = m.dehydrated;
                        null !== q && bd(q);
                      }
                    }
                  }
                  break;
                case 19:
                case 17:
                case 21:
                case 22:
                case 23:
                case 25:
                  break;
                default:
                  throw Error(p(163));
              }
              U || b.flags & 512 && Rj(b);
            } catch (r) {
              W(b, b.return, r);
            }
          }
          if (b === a) {
            V = null;
            break;
          }
          c = b.sibling;
          if (null !== c) {
            c.return = b.return;
            V = c;
            break;
          }
          V = b.return;
        }
      }
      function gk(a) {
        for (; null !== V; ) {
          var b = V;
          if (b === a) {
            V = null;
            break;
          }
          var c = b.sibling;
          if (null !== c) {
            c.return = b.return;
            V = c;
            break;
          }
          V = b.return;
        }
      }
      function jk(a) {
        for (; null !== V; ) {
          var b = V;
          try {
            switch (b.tag) {
              case 0:
              case 11:
              case 15:
                var c = b.return;
                try {
                  Qj(4, b);
                } catch (k) {
                  W(b, c, k);
                }
                break;
              case 1:
                var d = b.stateNode;
                if ("function" === typeof d.componentDidMount) {
                  var e = b.return;
                  try {
                    d.componentDidMount();
                  } catch (k) {
                    W(b, e, k);
                  }
                }
                var f = b.return;
                try {
                  Rj(b);
                } catch (k) {
                  W(b, f, k);
                }
                break;
              case 5:
                var g = b.return;
                try {
                  Rj(b);
                } catch (k) {
                  W(b, g, k);
                }
            }
          } catch (k) {
            W(b, b.return, k);
          }
          if (b === a) {
            V = null;
            break;
          }
          var h = b.sibling;
          if (null !== h) {
            h.return = b.return;
            V = h;
            break;
          }
          V = b.return;
        }
      }
      var lk = Math.ceil;
      var mk = ua.ReactCurrentDispatcher;
      var nk = ua.ReactCurrentOwner;
      var ok = ua.ReactCurrentBatchConfig;
      var K = 0;
      var Q = null;
      var Y = null;
      var Z = 0;
      var fj = 0;
      var ej = Uf(0);
      var T = 0;
      var pk = null;
      var rh = 0;
      var qk = 0;
      var rk = 0;
      var sk = null;
      var tk = null;
      var fk = 0;
      var Gj = Infinity;
      var uk = null;
      var Oi = false;
      var Pi = null;
      var Ri = null;
      var vk = false;
      var wk = null;
      var xk = 0;
      var yk = 0;
      var zk = null;
      var Ak = -1;
      var Bk = 0;
      function R() {
        return 0 !== (K & 6) ? B() : -1 !== Ak ? Ak : Ak = B();
      }
      function yi(a) {
        if (0 === (a.mode & 1)) return 1;
        if (0 !== (K & 2) && 0 !== Z) return Z & -Z;
        if (null !== Kg.transition) return 0 === Bk && (Bk = yc()), Bk;
        a = C;
        if (0 !== a) return a;
        a = window.event;
        a = void 0 === a ? 16 : jd(a.type);
        return a;
      }
      function gi(a, b, c, d) {
        if (50 < yk) throw yk = 0, zk = null, Error(p(185));
        Ac(a, c, d);
        if (0 === (K & 2) || a !== Q) a === Q && (0 === (K & 2) && (qk |= c), 4 === T && Ck(a, Z)), Dk(a, d), 1 === c && 0 === K && 0 === (b.mode & 1) && (Gj = B() + 500, fg && jg());
      }
      function Dk(a, b) {
        var c = a.callbackNode;
        wc(a, b);
        var d = uc(a, a === Q ? Z : 0);
        if (0 === d) null !== c && bc(c), a.callbackNode = null, a.callbackPriority = 0;
        else if (b = d & -d, a.callbackPriority !== b) {
          null != c && bc(c);
          if (1 === b) 0 === a.tag ? ig(Ek.bind(null, a)) : hg(Ek.bind(null, a)), Jf(function() {
            0 === (K & 6) && jg();
          }), c = null;
          else {
            switch (Dc(d)) {
              case 1:
                c = fc;
                break;
              case 4:
                c = gc;
                break;
              case 16:
                c = hc;
                break;
              case 536870912:
                c = jc;
                break;
              default:
                c = hc;
            }
            c = Fk(c, Gk.bind(null, a));
          }
          a.callbackPriority = b;
          a.callbackNode = c;
        }
      }
      function Gk(a, b) {
        Ak = -1;
        Bk = 0;
        if (0 !== (K & 6)) throw Error(p(327));
        var c = a.callbackNode;
        if (Hk() && a.callbackNode !== c) return null;
        var d = uc(a, a === Q ? Z : 0);
        if (0 === d) return null;
        if (0 !== (d & 30) || 0 !== (d & a.expiredLanes) || b) b = Ik(a, d);
        else {
          b = d;
          var e = K;
          K |= 2;
          var f = Jk();
          if (Q !== a || Z !== b) uk = null, Gj = B() + 500, Kk(a, b);
          do
            try {
              Lk();
              break;
            } catch (h) {
              Mk(a, h);
            }
          while (1);
          $g();
          mk.current = f;
          K = e;
          null !== Y ? b = 0 : (Q = null, Z = 0, b = T);
        }
        if (0 !== b) {
          2 === b && (e = xc(a), 0 !== e && (d = e, b = Nk(a, e)));
          if (1 === b) throw c = pk, Kk(a, 0), Ck(a, d), Dk(a, B()), c;
          if (6 === b) Ck(a, d);
          else {
            e = a.current.alternate;
            if (0 === (d & 30) && !Ok(e) && (b = Ik(a, d), 2 === b && (f = xc(a), 0 !== f && (d = f, b = Nk(a, f))), 1 === b)) throw c = pk, Kk(a, 0), Ck(a, d), Dk(a, B()), c;
            a.finishedWork = e;
            a.finishedLanes = d;
            switch (b) {
              case 0:
              case 1:
                throw Error(p(345));
              case 2:
                Pk(a, tk, uk);
                break;
              case 3:
                Ck(a, d);
                if ((d & 130023424) === d && (b = fk + 500 - B(), 10 < b)) {
                  if (0 !== uc(a, 0)) break;
                  e = a.suspendedLanes;
                  if ((e & d) !== d) {
                    R();
                    a.pingedLanes |= a.suspendedLanes & e;
                    break;
                  }
                  a.timeoutHandle = Ff(Pk.bind(null, a, tk, uk), b);
                  break;
                }
                Pk(a, tk, uk);
                break;
              case 4:
                Ck(a, d);
                if ((d & 4194240) === d) break;
                b = a.eventTimes;
                for (e = -1; 0 < d; ) {
                  var g = 31 - oc(d);
                  f = 1 << g;
                  g = b[g];
                  g > e && (e = g);
                  d &= ~f;
                }
                d = e;
                d = B() - d;
                d = (120 > d ? 120 : 480 > d ? 480 : 1080 > d ? 1080 : 1920 > d ? 1920 : 3e3 > d ? 3e3 : 4320 > d ? 4320 : 1960 * lk(d / 1960)) - d;
                if (10 < d) {
                  a.timeoutHandle = Ff(Pk.bind(null, a, tk, uk), d);
                  break;
                }
                Pk(a, tk, uk);
                break;
              case 5:
                Pk(a, tk, uk);
                break;
              default:
                throw Error(p(329));
            }
          }
        }
        Dk(a, B());
        return a.callbackNode === c ? Gk.bind(null, a) : null;
      }
      function Nk(a, b) {
        var c = sk;
        a.current.memoizedState.isDehydrated && (Kk(a, b).flags |= 256);
        a = Ik(a, b);
        2 !== a && (b = tk, tk = c, null !== b && Fj(b));
        return a;
      }
      function Fj(a) {
        null === tk ? tk = a : tk.push.apply(tk, a);
      }
      function Ok(a) {
        for (var b = a; ; ) {
          if (b.flags & 16384) {
            var c = b.updateQueue;
            if (null !== c && (c = c.stores, null !== c)) for (var d = 0; d < c.length; d++) {
              var e = c[d], f = e.getSnapshot;
              e = e.value;
              try {
                if (!He(f(), e)) return false;
              } catch (g) {
                return false;
              }
            }
          }
          c = b.child;
          if (b.subtreeFlags & 16384 && null !== c) c.return = b, b = c;
          else {
            if (b === a) break;
            for (; null === b.sibling; ) {
              if (null === b.return || b.return === a) return true;
              b = b.return;
            }
            b.sibling.return = b.return;
            b = b.sibling;
          }
        }
        return true;
      }
      function Ck(a, b) {
        b &= ~rk;
        b &= ~qk;
        a.suspendedLanes |= b;
        a.pingedLanes &= ~b;
        for (a = a.expirationTimes; 0 < b; ) {
          var c = 31 - oc(b), d = 1 << c;
          a[c] = -1;
          b &= ~d;
        }
      }
      function Ek(a) {
        if (0 !== (K & 6)) throw Error(p(327));
        Hk();
        var b = uc(a, 0);
        if (0 === (b & 1)) return Dk(a, B()), null;
        var c = Ik(a, b);
        if (0 !== a.tag && 2 === c) {
          var d = xc(a);
          0 !== d && (b = d, c = Nk(a, d));
        }
        if (1 === c) throw c = pk, Kk(a, 0), Ck(a, b), Dk(a, B()), c;
        if (6 === c) throw Error(p(345));
        a.finishedWork = a.current.alternate;
        a.finishedLanes = b;
        Pk(a, tk, uk);
        Dk(a, B());
        return null;
      }
      function Qk(a, b) {
        var c = K;
        K |= 1;
        try {
          return a(b);
        } finally {
          K = c, 0 === K && (Gj = B() + 500, fg && jg());
        }
      }
      function Rk(a) {
        null !== wk && 0 === wk.tag && 0 === (K & 6) && Hk();
        var b = K;
        K |= 1;
        var c = ok.transition, d = C;
        try {
          if (ok.transition = null, C = 1, a) return a();
        } finally {
          C = d, ok.transition = c, K = b, 0 === (K & 6) && jg();
        }
      }
      function Hj() {
        fj = ej.current;
        E(ej);
      }
      function Kk(a, b) {
        a.finishedWork = null;
        a.finishedLanes = 0;
        var c = a.timeoutHandle;
        -1 !== c && (a.timeoutHandle = -1, Gf(c));
        if (null !== Y) for (c = Y.return; null !== c; ) {
          var d = c;
          wg(d);
          switch (d.tag) {
            case 1:
              d = d.type.childContextTypes;
              null !== d && void 0 !== d && $f();
              break;
            case 3:
              zh();
              E(Wf);
              E(H);
              Eh();
              break;
            case 5:
              Bh(d);
              break;
            case 4:
              zh();
              break;
            case 13:
              E(L);
              break;
            case 19:
              E(L);
              break;
            case 10:
              ah(d.type._context);
              break;
            case 22:
            case 23:
              Hj();
          }
          c = c.return;
        }
        Q = a;
        Y = a = Pg(a.current, null);
        Z = fj = b;
        T = 0;
        pk = null;
        rk = qk = rh = 0;
        tk = sk = null;
        if (null !== fh) {
          for (b = 0; b < fh.length; b++) if (c = fh[b], d = c.interleaved, null !== d) {
            c.interleaved = null;
            var e = d.next, f = c.pending;
            if (null !== f) {
              var g = f.next;
              f.next = e;
              d.next = g;
            }
            c.pending = d;
          }
          fh = null;
        }
        return a;
      }
      function Mk(a, b) {
        do {
          var c = Y;
          try {
            $g();
            Fh.current = Rh;
            if (Ih) {
              for (var d = M.memoizedState; null !== d; ) {
                var e = d.queue;
                null !== e && (e.pending = null);
                d = d.next;
              }
              Ih = false;
            }
            Hh = 0;
            O = N = M = null;
            Jh = false;
            Kh = 0;
            nk.current = null;
            if (null === c || null === c.return) {
              T = 1;
              pk = b;
              Y = null;
              break;
            }
            a: {
              var f = a, g = c.return, h = c, k = b;
              b = Z;
              h.flags |= 32768;
              if (null !== k && "object" === typeof k && "function" === typeof k.then) {
                var l = k, m = h, q = m.tag;
                if (0 === (m.mode & 1) && (0 === q || 11 === q || 15 === q)) {
                  var r = m.alternate;
                  r ? (m.updateQueue = r.updateQueue, m.memoizedState = r.memoizedState, m.lanes = r.lanes) : (m.updateQueue = null, m.memoizedState = null);
                }
                var y = Ui(g);
                if (null !== y) {
                  y.flags &= -257;
                  Vi(y, g, h, f, b);
                  y.mode & 1 && Si(f, l, b);
                  b = y;
                  k = l;
                  var n = b.updateQueue;
                  if (null === n) {
                    var t = /* @__PURE__ */ new Set();
                    t.add(k);
                    b.updateQueue = t;
                  } else n.add(k);
                  break a;
                } else {
                  if (0 === (b & 1)) {
                    Si(f, l, b);
                    tj();
                    break a;
                  }
                  k = Error(p(426));
                }
              } else if (I && h.mode & 1) {
                var J = Ui(g);
                if (null !== J) {
                  0 === (J.flags & 65536) && (J.flags |= 256);
                  Vi(J, g, h, f, b);
                  Jg(Ji(k, h));
                  break a;
                }
              }
              f = k = Ji(k, h);
              4 !== T && (T = 2);
              null === sk ? sk = [f] : sk.push(f);
              f = g;
              do {
                switch (f.tag) {
                  case 3:
                    f.flags |= 65536;
                    b &= -b;
                    f.lanes |= b;
                    var x = Ni(f, k, b);
                    ph(f, x);
                    break a;
                  case 1:
                    h = k;
                    var w = f.type, u = f.stateNode;
                    if (0 === (f.flags & 128) && ("function" === typeof w.getDerivedStateFromError || null !== u && "function" === typeof u.componentDidCatch && (null === Ri || !Ri.has(u)))) {
                      f.flags |= 65536;
                      b &= -b;
                      f.lanes |= b;
                      var F = Qi(f, h, b);
                      ph(f, F);
                      break a;
                    }
                }
                f = f.return;
              } while (null !== f);
            }
            Sk(c);
          } catch (na) {
            b = na;
            Y === c && null !== c && (Y = c = c.return);
            continue;
          }
          break;
        } while (1);
      }
      function Jk() {
        var a = mk.current;
        mk.current = Rh;
        return null === a ? Rh : a;
      }
      function tj() {
        if (0 === T || 3 === T || 2 === T) T = 4;
        null === Q || 0 === (rh & 268435455) && 0 === (qk & 268435455) || Ck(Q, Z);
      }
      function Ik(a, b) {
        var c = K;
        K |= 2;
        var d = Jk();
        if (Q !== a || Z !== b) uk = null, Kk(a, b);
        do
          try {
            Tk();
            break;
          } catch (e) {
            Mk(a, e);
          }
        while (1);
        $g();
        K = c;
        mk.current = d;
        if (null !== Y) throw Error(p(261));
        Q = null;
        Z = 0;
        return T;
      }
      function Tk() {
        for (; null !== Y; ) Uk(Y);
      }
      function Lk() {
        for (; null !== Y && !cc(); ) Uk(Y);
      }
      function Uk(a) {
        var b = Vk(a.alternate, a, fj);
        a.memoizedProps = a.pendingProps;
        null === b ? Sk(a) : Y = b;
        nk.current = null;
      }
      function Sk(a) {
        var b = a;
        do {
          var c = b.alternate;
          a = b.return;
          if (0 === (b.flags & 32768)) {
            if (c = Ej(c, b, fj), null !== c) {
              Y = c;
              return;
            }
          } else {
            c = Ij(c, b);
            if (null !== c) {
              c.flags &= 32767;
              Y = c;
              return;
            }
            if (null !== a) a.flags |= 32768, a.subtreeFlags = 0, a.deletions = null;
            else {
              T = 6;
              Y = null;
              return;
            }
          }
          b = b.sibling;
          if (null !== b) {
            Y = b;
            return;
          }
          Y = b = a;
        } while (null !== b);
        0 === T && (T = 5);
      }
      function Pk(a, b, c) {
        var d = C, e = ok.transition;
        try {
          ok.transition = null, C = 1, Wk(a, b, c, d);
        } finally {
          ok.transition = e, C = d;
        }
        return null;
      }
      function Wk(a, b, c, d) {
        do
          Hk();
        while (null !== wk);
        if (0 !== (K & 6)) throw Error(p(327));
        c = a.finishedWork;
        var e = a.finishedLanes;
        if (null === c) return null;
        a.finishedWork = null;
        a.finishedLanes = 0;
        if (c === a.current) throw Error(p(177));
        a.callbackNode = null;
        a.callbackPriority = 0;
        var f = c.lanes | c.childLanes;
        Bc(a, f);
        a === Q && (Y = Q = null, Z = 0);
        0 === (c.subtreeFlags & 2064) && 0 === (c.flags & 2064) || vk || (vk = true, Fk(hc, function() {
          Hk();
          return null;
        }));
        f = 0 !== (c.flags & 15990);
        if (0 !== (c.subtreeFlags & 15990) || f) {
          f = ok.transition;
          ok.transition = null;
          var g = C;
          C = 1;
          var h = K;
          K |= 4;
          nk.current = null;
          Oj(a, c);
          dk(c, a);
          Oe(Df);
          dd = !!Cf;
          Df = Cf = null;
          a.current = c;
          hk(c, a, e);
          dc();
          K = h;
          C = g;
          ok.transition = f;
        } else a.current = c;
        vk && (vk = false, wk = a, xk = e);
        f = a.pendingLanes;
        0 === f && (Ri = null);
        mc(c.stateNode, d);
        Dk(a, B());
        if (null !== b) for (d = a.onRecoverableError, c = 0; c < b.length; c++) e = b[c], d(e.value, { componentStack: e.stack, digest: e.digest });
        if (Oi) throw Oi = false, a = Pi, Pi = null, a;
        0 !== (xk & 1) && 0 !== a.tag && Hk();
        f = a.pendingLanes;
        0 !== (f & 1) ? a === zk ? yk++ : (yk = 0, zk = a) : yk = 0;
        jg();
        return null;
      }
      function Hk() {
        if (null !== wk) {
          var a = Dc(xk), b = ok.transition, c = C;
          try {
            ok.transition = null;
            C = 16 > a ? 16 : a;
            if (null === wk) var d = false;
            else {
              a = wk;
              wk = null;
              xk = 0;
              if (0 !== (K & 6)) throw Error(p(331));
              var e = K;
              K |= 4;
              for (V = a.current; null !== V; ) {
                var f = V, g = f.child;
                if (0 !== (V.flags & 16)) {
                  var h = f.deletions;
                  if (null !== h) {
                    for (var k = 0; k < h.length; k++) {
                      var l = h[k];
                      for (V = l; null !== V; ) {
                        var m = V;
                        switch (m.tag) {
                          case 0:
                          case 11:
                          case 15:
                            Pj(8, m, f);
                        }
                        var q = m.child;
                        if (null !== q) q.return = m, V = q;
                        else for (; null !== V; ) {
                          m = V;
                          var r = m.sibling, y = m.return;
                          Sj(m);
                          if (m === l) {
                            V = null;
                            break;
                          }
                          if (null !== r) {
                            r.return = y;
                            V = r;
                            break;
                          }
                          V = y;
                        }
                      }
                    }
                    var n = f.alternate;
                    if (null !== n) {
                      var t = n.child;
                      if (null !== t) {
                        n.child = null;
                        do {
                          var J = t.sibling;
                          t.sibling = null;
                          t = J;
                        } while (null !== t);
                      }
                    }
                    V = f;
                  }
                }
                if (0 !== (f.subtreeFlags & 2064) && null !== g) g.return = f, V = g;
                else b: for (; null !== V; ) {
                  f = V;
                  if (0 !== (f.flags & 2048)) switch (f.tag) {
                    case 0:
                    case 11:
                    case 15:
                      Pj(9, f, f.return);
                  }
                  var x = f.sibling;
                  if (null !== x) {
                    x.return = f.return;
                    V = x;
                    break b;
                  }
                  V = f.return;
                }
              }
              var w = a.current;
              for (V = w; null !== V; ) {
                g = V;
                var u = g.child;
                if (0 !== (g.subtreeFlags & 2064) && null !== u) u.return = g, V = u;
                else b: for (g = w; null !== V; ) {
                  h = V;
                  if (0 !== (h.flags & 2048)) try {
                    switch (h.tag) {
                      case 0:
                      case 11:
                      case 15:
                        Qj(9, h);
                    }
                  } catch (na) {
                    W(h, h.return, na);
                  }
                  if (h === g) {
                    V = null;
                    break b;
                  }
                  var F = h.sibling;
                  if (null !== F) {
                    F.return = h.return;
                    V = F;
                    break b;
                  }
                  V = h.return;
                }
              }
              K = e;
              jg();
              if (lc && "function" === typeof lc.onPostCommitFiberRoot) try {
                lc.onPostCommitFiberRoot(kc, a);
              } catch (na) {
              }
              d = true;
            }
            return d;
          } finally {
            C = c, ok.transition = b;
          }
        }
        return false;
      }
      function Xk(a, b, c) {
        b = Ji(c, b);
        b = Ni(a, b, 1);
        a = nh(a, b, 1);
        b = R();
        null !== a && (Ac(a, 1, b), Dk(a, b));
      }
      function W(a, b, c) {
        if (3 === a.tag) Xk(a, a, c);
        else for (; null !== b; ) {
          if (3 === b.tag) {
            Xk(b, a, c);
            break;
          } else if (1 === b.tag) {
            var d = b.stateNode;
            if ("function" === typeof b.type.getDerivedStateFromError || "function" === typeof d.componentDidCatch && (null === Ri || !Ri.has(d))) {
              a = Ji(c, a);
              a = Qi(b, a, 1);
              b = nh(b, a, 1);
              a = R();
              null !== b && (Ac(b, 1, a), Dk(b, a));
              break;
            }
          }
          b = b.return;
        }
      }
      function Ti(a, b, c) {
        var d = a.pingCache;
        null !== d && d.delete(b);
        b = R();
        a.pingedLanes |= a.suspendedLanes & c;
        Q === a && (Z & c) === c && (4 === T || 3 === T && (Z & 130023424) === Z && 500 > B() - fk ? Kk(a, 0) : rk |= c);
        Dk(a, b);
      }
      function Yk(a, b) {
        0 === b && (0 === (a.mode & 1) ? b = 1 : (b = sc, sc <<= 1, 0 === (sc & 130023424) && (sc = 4194304)));
        var c = R();
        a = ih(a, b);
        null !== a && (Ac(a, b, c), Dk(a, c));
      }
      function uj(a) {
        var b = a.memoizedState, c = 0;
        null !== b && (c = b.retryLane);
        Yk(a, c);
      }
      function bk(a, b) {
        var c = 0;
        switch (a.tag) {
          case 13:
            var d = a.stateNode;
            var e = a.memoizedState;
            null !== e && (c = e.retryLane);
            break;
          case 19:
            d = a.stateNode;
            break;
          default:
            throw Error(p(314));
        }
        null !== d && d.delete(b);
        Yk(a, c);
      }
      var Vk;
      Vk = function(a, b, c) {
        if (null !== a) if (a.memoizedProps !== b.pendingProps || Wf.current) dh = true;
        else {
          if (0 === (a.lanes & c) && 0 === (b.flags & 128)) return dh = false, yj(a, b, c);
          dh = 0 !== (a.flags & 131072) ? true : false;
        }
        else dh = false, I && 0 !== (b.flags & 1048576) && ug(b, ng, b.index);
        b.lanes = 0;
        switch (b.tag) {
          case 2:
            var d = b.type;
            ij(a, b);
            a = b.pendingProps;
            var e = Yf(b, H.current);
            ch(b, c);
            e = Nh(null, b, d, a, e, c);
            var f = Sh();
            b.flags |= 1;
            "object" === typeof e && null !== e && "function" === typeof e.render && void 0 === e.$$typeof ? (b.tag = 1, b.memoizedState = null, b.updateQueue = null, Zf(d) ? (f = true, cg(b)) : f = false, b.memoizedState = null !== e.state && void 0 !== e.state ? e.state : null, kh(b), e.updater = Ei, b.stateNode = e, e._reactInternals = b, Ii(b, d, a, c), b = jj(null, b, d, true, f, c)) : (b.tag = 0, I && f && vg(b), Xi(null, b, e, c), b = b.child);
            return b;
          case 16:
            d = b.elementType;
            a: {
              ij(a, b);
              a = b.pendingProps;
              e = d._init;
              d = e(d._payload);
              b.type = d;
              e = b.tag = Zk(d);
              a = Ci(d, a);
              switch (e) {
                case 0:
                  b = cj(null, b, d, a, c);
                  break a;
                case 1:
                  b = hj(null, b, d, a, c);
                  break a;
                case 11:
                  b = Yi(null, b, d, a, c);
                  break a;
                case 14:
                  b = $i(null, b, d, Ci(d.type, a), c);
                  break a;
              }
              throw Error(p(
                306,
                d,
                ""
              ));
            }
            return b;
          case 0:
            return d = b.type, e = b.pendingProps, e = b.elementType === d ? e : Ci(d, e), cj(a, b, d, e, c);
          case 1:
            return d = b.type, e = b.pendingProps, e = b.elementType === d ? e : Ci(d, e), hj(a, b, d, e, c);
          case 3:
            a: {
              kj(b);
              if (null === a) throw Error(p(387));
              d = b.pendingProps;
              f = b.memoizedState;
              e = f.element;
              lh(a, b);
              qh(b, d, null, c);
              var g = b.memoizedState;
              d = g.element;
              if (f.isDehydrated) if (f = { element: d, isDehydrated: false, cache: g.cache, pendingSuspenseBoundaries: g.pendingSuspenseBoundaries, transitions: g.transitions }, b.updateQueue.baseState = f, b.memoizedState = f, b.flags & 256) {
                e = Ji(Error(p(423)), b);
                b = lj(a, b, d, c, e);
                break a;
              } else if (d !== e) {
                e = Ji(Error(p(424)), b);
                b = lj(a, b, d, c, e);
                break a;
              } else for (yg = Lf(b.stateNode.containerInfo.firstChild), xg = b, I = true, zg = null, c = Vg(b, null, d, c), b.child = c; c; ) c.flags = c.flags & -3 | 4096, c = c.sibling;
              else {
                Ig();
                if (d === e) {
                  b = Zi(a, b, c);
                  break a;
                }
                Xi(a, b, d, c);
              }
              b = b.child;
            }
            return b;
          case 5:
            return Ah(b), null === a && Eg(b), d = b.type, e = b.pendingProps, f = null !== a ? a.memoizedProps : null, g = e.children, Ef(d, e) ? g = null : null !== f && Ef(d, f) && (b.flags |= 32), gj(a, b), Xi(a, b, g, c), b.child;
          case 6:
            return null === a && Eg(b), null;
          case 13:
            return oj(a, b, c);
          case 4:
            return yh(b, b.stateNode.containerInfo), d = b.pendingProps, null === a ? b.child = Ug(b, null, d, c) : Xi(a, b, d, c), b.child;
          case 11:
            return d = b.type, e = b.pendingProps, e = b.elementType === d ? e : Ci(d, e), Yi(a, b, d, e, c);
          case 7:
            return Xi(a, b, b.pendingProps, c), b.child;
          case 8:
            return Xi(a, b, b.pendingProps.children, c), b.child;
          case 12:
            return Xi(a, b, b.pendingProps.children, c), b.child;
          case 10:
            a: {
              d = b.type._context;
              e = b.pendingProps;
              f = b.memoizedProps;
              g = e.value;
              G(Wg, d._currentValue);
              d._currentValue = g;
              if (null !== f) if (He(f.value, g)) {
                if (f.children === e.children && !Wf.current) {
                  b = Zi(a, b, c);
                  break a;
                }
              } else for (f = b.child, null !== f && (f.return = b); null !== f; ) {
                var h = f.dependencies;
                if (null !== h) {
                  g = f.child;
                  for (var k = h.firstContext; null !== k; ) {
                    if (k.context === d) {
                      if (1 === f.tag) {
                        k = mh(-1, c & -c);
                        k.tag = 2;
                        var l = f.updateQueue;
                        if (null !== l) {
                          l = l.shared;
                          var m = l.pending;
                          null === m ? k.next = k : (k.next = m.next, m.next = k);
                          l.pending = k;
                        }
                      }
                      f.lanes |= c;
                      k = f.alternate;
                      null !== k && (k.lanes |= c);
                      bh(
                        f.return,
                        c,
                        b
                      );
                      h.lanes |= c;
                      break;
                    }
                    k = k.next;
                  }
                } else if (10 === f.tag) g = f.type === b.type ? null : f.child;
                else if (18 === f.tag) {
                  g = f.return;
                  if (null === g) throw Error(p(341));
                  g.lanes |= c;
                  h = g.alternate;
                  null !== h && (h.lanes |= c);
                  bh(g, c, b);
                  g = f.sibling;
                } else g = f.child;
                if (null !== g) g.return = f;
                else for (g = f; null !== g; ) {
                  if (g === b) {
                    g = null;
                    break;
                  }
                  f = g.sibling;
                  if (null !== f) {
                    f.return = g.return;
                    g = f;
                    break;
                  }
                  g = g.return;
                }
                f = g;
              }
              Xi(a, b, e.children, c);
              b = b.child;
            }
            return b;
          case 9:
            return e = b.type, d = b.pendingProps.children, ch(b, c), e = eh(e), d = d(e), b.flags |= 1, Xi(a, b, d, c), b.child;
          case 14:
            return d = b.type, e = Ci(d, b.pendingProps), e = Ci(d.type, e), $i(a, b, d, e, c);
          case 15:
            return bj(a, b, b.type, b.pendingProps, c);
          case 17:
            return d = b.type, e = b.pendingProps, e = b.elementType === d ? e : Ci(d, e), ij(a, b), b.tag = 1, Zf(d) ? (a = true, cg(b)) : a = false, ch(b, c), Gi(b, d, e), Ii(b, d, e, c), jj(null, b, d, true, a, c);
          case 19:
            return xj(a, b, c);
          case 22:
            return dj(a, b, c);
        }
        throw Error(p(156, b.tag));
      };
      function Fk(a, b) {
        return ac(a, b);
      }
      function $k(a, b, c, d) {
        this.tag = a;
        this.key = c;
        this.sibling = this.child = this.return = this.stateNode = this.type = this.elementType = null;
        this.index = 0;
        this.ref = null;
        this.pendingProps = b;
        this.dependencies = this.memoizedState = this.updateQueue = this.memoizedProps = null;
        this.mode = d;
        this.subtreeFlags = this.flags = 0;
        this.deletions = null;
        this.childLanes = this.lanes = 0;
        this.alternate = null;
      }
      function Bg(a, b, c, d) {
        return new $k(a, b, c, d);
      }
      function aj(a) {
        a = a.prototype;
        return !(!a || !a.isReactComponent);
      }
      function Zk(a) {
        if ("function" === typeof a) return aj(a) ? 1 : 0;
        if (void 0 !== a && null !== a) {
          a = a.$$typeof;
          if (a === Da) return 11;
          if (a === Ga) return 14;
        }
        return 2;
      }
      function Pg(a, b) {
        var c = a.alternate;
        null === c ? (c = Bg(a.tag, b, a.key, a.mode), c.elementType = a.elementType, c.type = a.type, c.stateNode = a.stateNode, c.alternate = a, a.alternate = c) : (c.pendingProps = b, c.type = a.type, c.flags = 0, c.subtreeFlags = 0, c.deletions = null);
        c.flags = a.flags & 14680064;
        c.childLanes = a.childLanes;
        c.lanes = a.lanes;
        c.child = a.child;
        c.memoizedProps = a.memoizedProps;
        c.memoizedState = a.memoizedState;
        c.updateQueue = a.updateQueue;
        b = a.dependencies;
        c.dependencies = null === b ? null : { lanes: b.lanes, firstContext: b.firstContext };
        c.sibling = a.sibling;
        c.index = a.index;
        c.ref = a.ref;
        return c;
      }
      function Rg(a, b, c, d, e, f) {
        var g = 2;
        d = a;
        if ("function" === typeof a) aj(a) && (g = 1);
        else if ("string" === typeof a) g = 5;
        else a: switch (a) {
          case ya:
            return Tg(c.children, e, f, b);
          case za:
            g = 8;
            e |= 8;
            break;
          case Aa:
            return a = Bg(12, c, b, e | 2), a.elementType = Aa, a.lanes = f, a;
          case Ea:
            return a = Bg(13, c, b, e), a.elementType = Ea, a.lanes = f, a;
          case Fa:
            return a = Bg(19, c, b, e), a.elementType = Fa, a.lanes = f, a;
          case Ia:
            return pj(c, e, f, b);
          default:
            if ("object" === typeof a && null !== a) switch (a.$$typeof) {
              case Ba:
                g = 10;
                break a;
              case Ca:
                g = 9;
                break a;
              case Da:
                g = 11;
                break a;
              case Ga:
                g = 14;
                break a;
              case Ha:
                g = 16;
                d = null;
                break a;
            }
            throw Error(p(130, null == a ? a : typeof a, ""));
        }
        b = Bg(g, c, b, e);
        b.elementType = a;
        b.type = d;
        b.lanes = f;
        return b;
      }
      function Tg(a, b, c, d) {
        a = Bg(7, a, d, b);
        a.lanes = c;
        return a;
      }
      function pj(a, b, c, d) {
        a = Bg(22, a, d, b);
        a.elementType = Ia;
        a.lanes = c;
        a.stateNode = { isHidden: false };
        return a;
      }
      function Qg(a, b, c) {
        a = Bg(6, a, null, b);
        a.lanes = c;
        return a;
      }
      function Sg(a, b, c) {
        b = Bg(4, null !== a.children ? a.children : [], a.key, b);
        b.lanes = c;
        b.stateNode = { containerInfo: a.containerInfo, pendingChildren: null, implementation: a.implementation };
        return b;
      }
      function al(a, b, c, d, e) {
        this.tag = b;
        this.containerInfo = a;
        this.finishedWork = this.pingCache = this.current = this.pendingChildren = null;
        this.timeoutHandle = -1;
        this.callbackNode = this.pendingContext = this.context = null;
        this.callbackPriority = 0;
        this.eventTimes = zc(0);
        this.expirationTimes = zc(-1);
        this.entangledLanes = this.finishedLanes = this.mutableReadLanes = this.expiredLanes = this.pingedLanes = this.suspendedLanes = this.pendingLanes = 0;
        this.entanglements = zc(0);
        this.identifierPrefix = d;
        this.onRecoverableError = e;
        this.mutableSourceEagerHydrationData = null;
      }
      function bl(a, b, c, d, e, f, g, h, k) {
        a = new al(a, b, c, h, k);
        1 === b ? (b = 1, true === f && (b |= 8)) : b = 0;
        f = Bg(3, null, null, b);
        a.current = f;
        f.stateNode = a;
        f.memoizedState = { element: d, isDehydrated: c, cache: null, transitions: null, pendingSuspenseBoundaries: null };
        kh(f);
        return a;
      }
      function cl(a, b, c) {
        var d = 3 < arguments.length && void 0 !== arguments[3] ? arguments[3] : null;
        return { $$typeof: wa, key: null == d ? null : "" + d, children: a, containerInfo: b, implementation: c };
      }
      function dl(a) {
        if (!a) return Vf;
        a = a._reactInternals;
        a: {
          if (Vb(a) !== a || 1 !== a.tag) throw Error(p(170));
          var b = a;
          do {
            switch (b.tag) {
              case 3:
                b = b.stateNode.context;
                break a;
              case 1:
                if (Zf(b.type)) {
                  b = b.stateNode.__reactInternalMemoizedMergedChildContext;
                  break a;
                }
            }
            b = b.return;
          } while (null !== b);
          throw Error(p(171));
        }
        if (1 === a.tag) {
          var c = a.type;
          if (Zf(c)) return bg(a, c, b);
        }
        return b;
      }
      function el(a, b, c, d, e, f, g, h, k) {
        a = bl(c, d, true, a, e, f, g, h, k);
        a.context = dl(null);
        c = a.current;
        d = R();
        e = yi(c);
        f = mh(d, e);
        f.callback = void 0 !== b && null !== b ? b : null;
        nh(c, f, e);
        a.current.lanes = e;
        Ac(a, e, d);
        Dk(a, d);
        return a;
      }
      function fl(a, b, c, d) {
        var e = b.current, f = R(), g = yi(e);
        c = dl(c);
        null === b.context ? b.context = c : b.pendingContext = c;
        b = mh(f, g);
        b.payload = { element: a };
        d = void 0 === d ? null : d;
        null !== d && (b.callback = d);
        a = nh(e, b, g);
        null !== a && (gi(a, e, g, f), oh(a, e, g));
        return g;
      }
      function gl(a) {
        a = a.current;
        if (!a.child) return null;
        switch (a.child.tag) {
          case 5:
            return a.child.stateNode;
          default:
            return a.child.stateNode;
        }
      }
      function hl(a, b) {
        a = a.memoizedState;
        if (null !== a && null !== a.dehydrated) {
          var c = a.retryLane;
          a.retryLane = 0 !== c && c < b ? c : b;
        }
      }
      function il(a, b) {
        hl(a, b);
        (a = a.alternate) && hl(a, b);
      }
      function jl() {
        return null;
      }
      var kl = "function" === typeof reportError ? reportError : function(a) {
        console.error(a);
      };
      function ll(a) {
        this._internalRoot = a;
      }
      ml.prototype.render = ll.prototype.render = function(a) {
        var b = this._internalRoot;
        if (null === b) throw Error(p(409));
        fl(a, b, null, null);
      };
      ml.prototype.unmount = ll.prototype.unmount = function() {
        var a = this._internalRoot;
        if (null !== a) {
          this._internalRoot = null;
          var b = a.containerInfo;
          Rk(function() {
            fl(null, a, null, null);
          });
          b[uf] = null;
        }
      };
      function ml(a) {
        this._internalRoot = a;
      }
      ml.prototype.unstable_scheduleHydration = function(a) {
        if (a) {
          var b = Hc();
          a = { blockedOn: null, target: a, priority: b };
          for (var c = 0; c < Qc.length && 0 !== b && b < Qc[c].priority; c++) ;
          Qc.splice(c, 0, a);
          0 === c && Vc(a);
        }
      };
      function nl(a) {
        return !(!a || 1 !== a.nodeType && 9 !== a.nodeType && 11 !== a.nodeType);
      }
      function ol(a) {
        return !(!a || 1 !== a.nodeType && 9 !== a.nodeType && 11 !== a.nodeType && (8 !== a.nodeType || " react-mount-point-unstable " !== a.nodeValue));
      }
      function pl() {
      }
      function ql(a, b, c, d, e) {
        if (e) {
          if ("function" === typeof d) {
            var f = d;
            d = function() {
              var a2 = gl(g);
              f.call(a2);
            };
          }
          var g = el(b, d, a, 0, null, false, false, "", pl);
          a._reactRootContainer = g;
          a[uf] = g.current;
          sf(8 === a.nodeType ? a.parentNode : a);
          Rk();
          return g;
        }
        for (; e = a.lastChild; ) a.removeChild(e);
        if ("function" === typeof d) {
          var h = d;
          d = function() {
            var a2 = gl(k);
            h.call(a2);
          };
        }
        var k = bl(a, 0, false, null, null, false, false, "", pl);
        a._reactRootContainer = k;
        a[uf] = k.current;
        sf(8 === a.nodeType ? a.parentNode : a);
        Rk(function() {
          fl(b, k, c, d);
        });
        return k;
      }
      function rl(a, b, c, d, e) {
        var f = c._reactRootContainer;
        if (f) {
          var g = f;
          if ("function" === typeof e) {
            var h = e;
            e = function() {
              var a2 = gl(g);
              h.call(a2);
            };
          }
          fl(b, g, a, e);
        } else g = ql(c, b, a, e, d);
        return gl(g);
      }
      Ec = function(a) {
        switch (a.tag) {
          case 3:
            var b = a.stateNode;
            if (b.current.memoizedState.isDehydrated) {
              var c = tc(b.pendingLanes);
              0 !== c && (Cc(b, c | 1), Dk(b, B()), 0 === (K & 6) && (Gj = B() + 500, jg()));
            }
            break;
          case 13:
            Rk(function() {
              var b2 = ih(a, 1);
              if (null !== b2) {
                var c2 = R();
                gi(b2, a, 1, c2);
              }
            }), il(a, 1);
        }
      };
      Fc = function(a) {
        if (13 === a.tag) {
          var b = ih(a, 134217728);
          if (null !== b) {
            var c = R();
            gi(b, a, 134217728, c);
          }
          il(a, 134217728);
        }
      };
      Gc = function(a) {
        if (13 === a.tag) {
          var b = yi(a), c = ih(a, b);
          if (null !== c) {
            var d = R();
            gi(c, a, b, d);
          }
          il(a, b);
        }
      };
      Hc = function() {
        return C;
      };
      Ic = function(a, b) {
        var c = C;
        try {
          return C = a, b();
        } finally {
          C = c;
        }
      };
      yb = function(a, b, c) {
        switch (b) {
          case "input":
            bb(a, c);
            b = c.name;
            if ("radio" === c.type && null != b) {
              for (c = a; c.parentNode; ) c = c.parentNode;
              c = c.querySelectorAll("input[name=" + JSON.stringify("" + b) + '][type="radio"]');
              for (b = 0; b < c.length; b++) {
                var d = c[b];
                if (d !== a && d.form === a.form) {
                  var e = Db(d);
                  if (!e) throw Error(p(90));
                  Wa(d);
                  bb(d, e);
                }
              }
            }
            break;
          case "textarea":
            ib(a, c);
            break;
          case "select":
            b = c.value, null != b && fb(a, !!c.multiple, b, false);
        }
      };
      Gb = Qk;
      Hb = Rk;
      var sl = { usingClientEntryPoint: false, Events: [Cb, ue, Db, Eb, Fb, Qk] };
      var tl = { findFiberByHostInstance: Wc, bundleType: 0, version: "18.3.1", rendererPackageName: "react-dom" };
      var ul = { bundleType: tl.bundleType, version: tl.version, rendererPackageName: tl.rendererPackageName, rendererConfig: tl.rendererConfig, overrideHookState: null, overrideHookStateDeletePath: null, overrideHookStateRenamePath: null, overrideProps: null, overridePropsDeletePath: null, overridePropsRenamePath: null, setErrorHandler: null, setSuspenseHandler: null, scheduleUpdate: null, currentDispatcherRef: ua.ReactCurrentDispatcher, findHostInstanceByFiber: function(a) {
        a = Zb(a);
        return null === a ? null : a.stateNode;
      }, findFiberByHostInstance: tl.findFiberByHostInstance || jl, findHostInstancesForRefresh: null, scheduleRefresh: null, scheduleRoot: null, setRefreshHandler: null, getCurrentFiber: null, reconcilerVersion: "18.3.1-next-f1338f8080-20240426" };
      if ("undefined" !== typeof __REACT_DEVTOOLS_GLOBAL_HOOK__) {
        vl = __REACT_DEVTOOLS_GLOBAL_HOOK__;
        if (!vl.isDisabled && vl.supportsFiber) try {
          kc = vl.inject(ul), lc = vl;
        } catch (a) {
        }
      }
      var vl;
      exports.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED = sl;
      exports.createPortal = function(a, b) {
        var c = 2 < arguments.length && void 0 !== arguments[2] ? arguments[2] : null;
        if (!nl(b)) throw Error(p(200));
        return cl(a, b, null, c);
      };
      exports.createRoot = function(a, b) {
        if (!nl(a)) throw Error(p(299));
        var c = false, d = "", e = kl;
        null !== b && void 0 !== b && (true === b.unstable_strictMode && (c = true), void 0 !== b.identifierPrefix && (d = b.identifierPrefix), void 0 !== b.onRecoverableError && (e = b.onRecoverableError));
        b = bl(a, 1, false, null, null, c, false, d, e);
        a[uf] = b.current;
        sf(8 === a.nodeType ? a.parentNode : a);
        return new ll(b);
      };
      exports.findDOMNode = function(a) {
        if (null == a) return null;
        if (1 === a.nodeType) return a;
        var b = a._reactInternals;
        if (void 0 === b) {
          if ("function" === typeof a.render) throw Error(p(188));
          a = Object.keys(a).join(",");
          throw Error(p(268, a));
        }
        a = Zb(b);
        a = null === a ? null : a.stateNode;
        return a;
      };
      exports.flushSync = function(a) {
        return Rk(a);
      };
      exports.hydrate = function(a, b, c) {
        if (!ol(b)) throw Error(p(200));
        return rl(null, a, b, true, c);
      };
      exports.hydrateRoot = function(a, b, c) {
        if (!nl(a)) throw Error(p(405));
        var d = null != c && c.hydratedSources || null, e = false, f = "", g = kl;
        null !== c && void 0 !== c && (true === c.unstable_strictMode && (e = true), void 0 !== c.identifierPrefix && (f = c.identifierPrefix), void 0 !== c.onRecoverableError && (g = c.onRecoverableError));
        b = el(b, null, a, 1, null != c ? c : null, e, false, f, g);
        a[uf] = b.current;
        sf(a);
        if (d) for (a = 0; a < d.length; a++) c = d[a], e = c._getVersion, e = e(c._source), null == b.mutableSourceEagerHydrationData ? b.mutableSourceEagerHydrationData = [c, e] : b.mutableSourceEagerHydrationData.push(
          c,
          e
        );
        return new ml(b);
      };
      exports.render = function(a, b, c) {
        if (!ol(b)) throw Error(p(200));
        return rl(null, a, b, false, c);
      };
      exports.unmountComponentAtNode = function(a) {
        if (!ol(a)) throw Error(p(40));
        return a._reactRootContainer ? (Rk(function() {
          rl(null, null, a, false, function() {
            a._reactRootContainer = null;
            a[uf] = null;
          });
        }), true) : false;
      };
      exports.unstable_batchedUpdates = Qk;
      exports.unstable_renderSubtreeIntoContainer = function(a, b, c, d) {
        if (!ol(c)) throw Error(p(200));
        if (null == a || void 0 === a._reactInternals) throw Error(p(38));
        return rl(a, b, c, false, d);
      };
      exports.version = "18.3.1-next-f1338f8080-20240426";
    }
  });

  // node_modules/react-dom/index.js
  var require_react_dom = __commonJS({
    "node_modules/react-dom/index.js"(exports, module) {
      "use strict";
      function checkDCE() {
        if (typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ === "undefined" || typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE !== "function") {
          return;
        }
        if (false) {
          throw new Error("^_^");
        }
        try {
          __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE(checkDCE);
        } catch (err) {
          console.error(err);
        }
      }
      if (true) {
        checkDCE();
        module.exports = require_react_dom_production_min();
      } else {
        module.exports = null;
      }
    }
  });

  // node_modules/react-dom/client.js
  var require_client = __commonJS({
    "node_modules/react-dom/client.js"(exports) {
      "use strict";
      var m = require_react_dom();
      if (true) {
        exports.createRoot = m.createRoot;
        exports.hydrateRoot = m.hydrateRoot;
      } else {
        i = m.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED;
        exports.createRoot = function(c, o) {
          i.usingClientEntryPoint = true;
          try {
            return m.createRoot(c, o);
          } finally {
            i.usingClientEntryPoint = false;
          }
        };
        exports.hydrateRoot = function(c, h, o) {
          i.usingClientEntryPoint = true;
          try {
            return m.hydrateRoot(c, h, o);
          } finally {
            i.usingClientEntryPoint = false;
          }
        };
      }
      var i;
    }
  });

  // node_modules/react/cjs/react-jsx-runtime.production.min.js
  var require_react_jsx_runtime_production_min = __commonJS({
    "node_modules/react/cjs/react-jsx-runtime.production.min.js"(exports) {
      "use strict";
      var f = require_react();
      var k = Symbol.for("react.element");
      var l = Symbol.for("react.fragment");
      var m = Object.prototype.hasOwnProperty;
      var n = f.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED.ReactCurrentOwner;
      var p = { key: true, ref: true, __self: true, __source: true };
      function q(c, a, g) {
        var b, d = {}, e = null, h = null;
        void 0 !== g && (e = "" + g);
        void 0 !== a.key && (e = "" + a.key);
        void 0 !== a.ref && (h = a.ref);
        for (b in a) m.call(a, b) && !p.hasOwnProperty(b) && (d[b] = a[b]);
        if (c && c.defaultProps) for (b in a = c.defaultProps, a) void 0 === d[b] && (d[b] = a[b]);
        return { $$typeof: k, type: c, key: e, ref: h, props: d, _owner: n.current };
      }
      exports.Fragment = l;
      exports.jsx = q;
      exports.jsxs = q;
    }
  });

  // node_modules/react/jsx-runtime.js
  var require_jsx_runtime = __commonJS({
    "node_modules/react/jsx-runtime.js"(exports, module) {
      "use strict";
      if (true) {
        module.exports = require_react_jsx_runtime_production_min();
      } else {
        module.exports = null;
      }
    }
  });

  // src/main.jsx
  var import_react6 = __toESM(require_react(), 1);
  var import_client = __toESM(require_client(), 1);

  // src/app.jsx
  var import_react5 = __toESM(require_react(), 1);

  // src/figures.jsx
  var import_react3 = __toESM(require_react(), 1);

  // node_modules/smiles-drawer/src/ArrayHelper.js
  var ArrayHelper = class _ArrayHelper {
    /**
     * Clone an array or an object. If an object is passed, a shallow clone will be created.
     *
     * @static
     * @param {*} arr The array or object to be cloned.
     * @returns {*} A clone of the array or object.
     */
    static clone(arr) {
      let out = Array.isArray(arr) ? [] : {};
      for (let key in arr) {
        let value = arr[key];
        if (typeof value.clone === "function") {
          out[key] = value.clone();
        } else {
          out[key] = typeof value === "object" ? _ArrayHelper.clone(value) : value;
        }
      }
      return out;
    }
    /**
     * Returns a boolean indicating whether or not the two arrays contain the same elements.
     * Only supports 1d, non-nested arrays.
     *
     * @static
     * @param {Array} arrA An array.
     * @param {Array} arrB An array.
     * @returns {Boolean} A boolean indicating whether or not the two arrays contain the same elements.
     */
    static equals(arrA, arrB) {
      if (arrA.length !== arrB.length) {
        return false;
      }
      let tmpA = arrA.slice().sort();
      let tmpB = arrB.slice().sort();
      for (let i = 0; i < tmpA.length; i++) {
        if (tmpA[i] !== tmpB[i]) {
          return false;
        }
      }
      return true;
    }
    /**
     * Returns a string representation of an array. If the array contains objects with an id property, the id property is printed for each of the elements.
     *
     * @static
     * @param {Object[]} arr An array.
     * @param {*} arr[].id If the array contains an object with the property 'id', the properties value is printed. Else, the array elements value is printend.
     * @returns {String} A string representation of the array.
     */
    static print(arr) {
      if (arr.length == 0) {
        return "";
      }
      let s = "(";
      for (let i = 0; i < arr.length; i++) {
        s += arr[i].id ? arr[i].id + ", " : arr[i] + ", ";
      }
      s = s.substring(0, s.length - 2);
      return s + ")";
    }
    /**
     * Run a function for each element in the array. The element is supplied as an argument for the callback function
     *
     * @static
     * @param {Array} arr An array.
     * @param {Function} callback The callback function that is called for each element.
     */
    static each(arr, callback) {
      for (let i = 0; i < arr.length; i++) {
        callback(arr[i]);
      }
    }
    /**
     * Return the array element from an array containing objects, where a property of the object is set to a given value.
     *
     * @static
     * @param {Array} arr An array.
     * @param {(String|Number)} property A property contained within an object in the array.
     * @param {(String|Number)} value The value of the property.
     * @returns {*} The array element matching the value.
     */
    static get(arr, property, value) {
      for (let i = 0; i < arr.length; i++) {
        if (arr[i][property] == value) {
          return arr[i];
        }
      }
    }
    /**
     * Checks whether or not an array contains a given value. the options object passed as a second argument can contain three properties. value: The value to be searched for. property: The property that is to be searched for a given value. func: A function that is used as a callback to return either true or false in order to do a custom comparison.
     *
     * @static
     * @param {Array} arr An array.
     * @param {Object} options See method description.
     * @param {*} options.value The value for which to check.
     * @param {String} [options.property=undefined] The property on which to check.
     * @param {Function} [options.func=undefined] A custom property function.
     * @returns {Boolean} A boolean whether or not the array contains a value.
     */
    static contains(arr, options) {
      if (!options.property && !options.func) {
        for (let i = 0; i < arr.length; i++) {
          if (arr[i] == options.value) {
            return true;
          }
        }
      } else if (options.func) {
        for (let i = 0; i < arr.length; i++) {
          if (options.func(arr[i])) {
            return true;
          }
        }
      } else {
        for (let i = 0; i < arr.length; i++) {
          if (arr[i][options.property] == options.value) {
            return true;
          }
        }
      }
      return false;
    }
    /**
     * Returns an array containing the intersection between two arrays. That is, values that are common to both arrays.
     *
     * @static
     * @param {Array} arrA An array.
     * @param {Array} arrB An array.
     * @returns {Array} The intersecting vlaues.
     */
    static intersection(arrA, arrB) {
      let intersection = [];
      for (let i = 0; i < arrA.length; i++) {
        for (let j = 0; j < arrB.length; j++) {
          if (arrA[i] === arrB[j]) {
            intersection.push(arrA[i]);
          }
        }
      }
      return intersection;
    }
    /**
     * Returns an array of unique elements contained in an array.
     *
     * @static
     * @param {Array} arr An array.
     * @returns {Array} An array of unique elements contained within the array supplied as an argument.
     */
    static unique(arr) {
      let contains = {};
      return arr.filter(function(i) {
        return contains[i] !== void 0 ? false : contains[i] = true;
      });
    }
    /**
     * Count the number of occurences of a value in an array.
     *
     * @static
     * @param {Array} arr An array.
     * @param {*} value A value to be counted.
     * @returns {Number} The number of occurences of a value in the array.
     */
    static count(arr, value) {
      let count = 0;
      for (let i = 0; i < arr.length; i++) {
        if (arr[i] === value) {
          count++;
        }
      }
      return count;
    }
    /**
     * Toggles the value of an array. If a value is not contained in an array, the array returned will contain all the values of the original array including the value. If a value is contained in an array, the array returned will contain all the values of the original array excluding the value.
     *
     * @static
     * @param {Array} arr An array.
     * @param {*} value A value to be toggled.
     * @returns {Array} The toggled array.
     */
    static toggle(arr, value) {
      let newArr = [];
      let removed = false;
      for (let i = 0; i < arr.length; i++) {
        if (arr[i] !== value) {
          newArr.push(arr[i]);
        } else {
          removed = true;
        }
      }
      if (!removed) {
        newArr.push(value);
      }
      return newArr;
    }
    /**
     * Remove a value from an array.
     *
     * @static
     * @param {Array} arr An array.
     * @param {*} value A value to be removed.
     * @returns {Array} A new array with the element with a given value removed.
     */
    static remove(arr, value) {
      let tmp = [];
      for (let i = 0; i < arr.length; i++) {
        if (arr[i] !== value) {
          tmp.push(arr[i]);
        }
      }
      return tmp;
    }
    /**
     * Remove a value from an array with unique values.
     *
     * @static
     * @param {Array} arr An array.
     * @param {*} value A value to be removed.
     * @returns {Array} An array with the element with a given value removed.
     */
    static removeUnique(arr, value) {
      let index = arr.indexOf(value);
      if (index > -1) {
        arr.splice(index, 1);
      }
      return arr;
    }
    /**
     * Remove all elements contained in one array from another array.
     *
     * @static
     * @param {Array} arrA The array to be filtered.
     * @param {Array} arrB The array containing elements that will be removed from the other array.
     * @returns {Array} The filtered array.
     */
    static removeAll(arrA, arrB) {
      return arrA.filter(function(item) {
        return arrB.indexOf(item) === -1;
      });
    }
    /**
     * Merges two arrays and returns the result. The first array will be appended to the second array.
     *
     * @static
     * @param {Array} arrA An array.
     * @param {Array} arrB An array.
     * @returns {Array} The merged array.
     */
    static merge(arrA, arrB) {
      let arr = new Array(arrA.length + arrB.length);
      for (let i = 0; i < arrA.length; i++) {
        arr[i] = arrA[i];
      }
      for (let i = 0; i < arrB.length; i++) {
        arr[arrA.length + i] = arrB[i];
      }
      return arr;
    }
    /**
     * Checks whether or not an array contains all the elements of another array, without regard to the order.
     *
     * @static
     * @param {Array} arrA An array.
     * @param {Array} arrB An array.
     * @returns {Boolean} A boolean indicating whether or not both array contain the same elements.
     */
    static containsAll(arrA, arrB) {
      let containing = 0;
      for (let i = 0; i < arrA.length; i++) {
        for (let j = 0; j < arrB.length; j++) {
          if (arrA[i] === arrB[j]) {
            containing++;
          }
        }
      }
      return containing === arrB.length;
    }
    /**
     * Sort an array of atomic number information. Where the number is indicated as x, x.y, x.y.z, ...
     *
     * @param {Object[]} arr An array of vertex ids with their associated atomic numbers.
     * @param {Number} arr[].vertexId A vertex id.
     * @param {String} arr[].atomicNumber The atomic number associated with the vertex id.
     * @returns {Object[]} The array sorted by atomic number. Example of an array entry: { atomicNumber: 2, vertexId: 5 }.
     */
    static sortByAtomicNumberDesc(arr) {
      let map = arr.map(function(e, i) {
        return { index: i, value: e.atomicNumber.split(".").map(Number) };
      });
      map.sort(function(a, b) {
        let min5 = Math.min(b.value.length, a.value.length);
        let i = 0;
        while (i < min5 && b.value[i] === a.value[i]) {
          i++;
        }
        return i === min5 ? b.value.length - a.value.length : b.value[i] - a.value[i];
      });
      return map.map(function(e) {
        return arr[e.index];
      });
    }
    /**
     * Copies a an n-dimensional array.
     *
     * @param {Array} arr The array to be copied.
     * @returns {Array} The copy.
     */
    static deepCopy(arr) {
      let newArr = [];
      for (let i = 0; i < arr.length; i++) {
        let item = arr[i];
        if (item instanceof Array) {
          newArr[i] = _ArrayHelper.deepCopy(item);
        } else {
          newArr[i] = item;
        }
      }
      return newArr;
    }
  };

  // node_modules/smiles-drawer/src/Atom.js
  var Atom = class _Atom {
    /**
     * The constructor of the class Atom.
     *
     * @param {String} element The one-letter code of the element.
     * @param {String} [bondType='-'] The type of the bond associated with this atom.
     */
    constructor(element, bondType = "-") {
      this.idx = null;
      this.element = element.length === 1 ? element.toUpperCase() : element;
      this.drawExplicit = false;
      this.ringbonds = [];
      this.rings = [];
      this.bondType = bondType;
      this.branchBond = null;
      this.isBridge = false;
      this.isBridgeNode = false;
      this.originalRings = [];
      this.bridgedRing = null;
      this.anchoredRings = [];
      this.bracket = null;
      this.plane = 0;
      this.attachedPseudoElements = {};
      this.hasAttachedPseudoElements = false;
      this.isDrawn = true;
      this.isConnectedToRing = false;
      this.neighbouringElements = [];
      this.isPartOfAromaticRing = element !== this.element;
      this.bondCount = 0;
      this.chirality = "";
      this.isStereoCenter = false;
      this.priority = 0;
      this.mainChain = false;
      this.hydrogenDirection = "down";
      this.subtreeDepth = 1;
      this.hasHydrogen = false;
      this.class = void 0;
    }
    /**
     * Adds a neighbouring element to this atom.
     *
     * @param {String} element A string representing an element.
     */
    addNeighbouringElement(element) {
      this.neighbouringElements.push(element);
    }
    /**
     * Attaches a pseudo element (e.g. Ac) to the atom.
     * @param {String} element The element identifier (e.g. Br, C, ...).
     * @param {String} previousElement The element that is part of the main chain (not the terminals that are converted to the pseudo element or concatinated).
     * @param {Number} [hydrogenCount=0] The number of hydrogens for the element.
     * @param {Number} [charge=0] The charge for the element.
     */
    attachPseudoElement(element, previousElement, hydrogenCount = 0, charge = 0) {
      if (hydrogenCount === null) {
        hydrogenCount = 0;
      }
      if (charge === null) {
        charge = 0;
      }
      let key = hydrogenCount + element + charge;
      if (this.attachedPseudoElements[key]) {
        this.attachedPseudoElements[key].count += 1;
      } else {
        this.attachedPseudoElements[key] = {
          element,
          count: 1,
          hydrogenCount,
          previousElement,
          charge
        };
      }
      this.hasAttachedPseudoElements = true;
    }
    /**
     * Returns the attached pseudo elements sorted by hydrogen count (ascending).
     *
     * @returns {Object} The sorted attached pseudo elements.
     */
    getAttachedPseudoElements() {
      let ordered = {};
      Object.keys(this.attachedPseudoElements).sort().forEach((key) => {
        ordered[key] = this.attachedPseudoElements[key];
      });
      return ordered;
    }
    /**
     * Returns the number of attached pseudo elements.
     *
     * @returns {Number} The number of attached pseudo elements.
     */
    getAttachedPseudoElementsCount() {
      return Object.keys(this.attachedPseudoElements).length;
    }
    /**
     * Returns whether this atom is a heteroatom (not C and not H).
     *
     * @returns {Boolean} A boolean indicating whether this atom is a heteroatom.
     */
    isHeteroAtom() {
      return this.element !== "C" && this.element !== "H";
    }
    /**
     * Defines this atom as the anchor for a ring. When doing repositionings of the vertices and the vertex associated with this atom is moved, the center of this ring is moved as well.
     *
     * @param {Number} ringId A ring id.
     */
    addAnchoredRing(ringId) {
      if (!ArrayHelper.contains(this.anchoredRings, { value: ringId })) {
        this.anchoredRings.push(ringId);
      }
    }
    /**
     * Returns the number of ringbonds (breaks in rings to generate the MST of the smiles) within this atom is connected to.
     *
     * @returns {Number} The number of ringbonds this atom is connected to.
     */
    getRingbondCount() {
      return this.ringbonds.length;
    }
    /**
     * Backs up the current rings.
     */
    backupRings() {
      this.originalRings = Array(this.rings.length);
      for (let i = 0; i < this.rings.length; i++) {
        this.originalRings[i] = this.rings[i];
      }
    }
    /**
     * Restores the most recent backed up rings.
     */
    restoreRings() {
      this.rings = Array(this.originalRings.length);
      for (let i = 0; i < this.originalRings.length; i++) {
        this.rings[i] = this.originalRings[i];
      }
    }
    /**
     * Checks whether or not two atoms share a common ringbond id. A ringbond is a break in a ring created when generating the spanning tree of a structure.
     *
     * @param {Atom} atomA An atom.
     * @param {Atom} atomB An atom.
     * @returns {Boolean} A boolean indicating whether or not two atoms share a common ringbond.
     */
    haveCommonRingbond(atomA, atomB) {
      for (let i = 0; i < atomA.ringbonds.length; i++) {
        for (let j = 0; j < atomB.ringbonds.length; j++) {
          if (atomA.ringbonds[i].id == atomB.ringbonds[j].id) {
            return true;
          }
        }
      }
      return false;
    }
    /**
     * Check whether or not the neighbouring elements of this atom equal the supplied array.
     *
     * @param {String[]} arr An array containing all the elements that are neighbouring this atom. E.g. ['C', 'O', 'O', 'N']
     * @returns {Boolean} A boolean indicating whether or not the neighbours match the supplied array of elements.
     */
    neighbouringElementsEqual(arr) {
      if (arr.length !== this.neighbouringElements.length) {
        return false;
      }
      arr.sort();
      this.neighbouringElements.sort();
      for (let i = 0; i < this.neighbouringElements.length; i++) {
        if (arr[i] !== this.neighbouringElements[i]) {
          return false;
        }
      }
      return true;
    }
    /**
     * Get the atomic number of this atom.
     *
     * @returns {Number} The atomic number of this atom.
     */
    getAtomicNumber() {
      return _Atom.atomicNumbers[this.element];
    }
    /**
     * Get the maximum number of bonds for this atom.
     *
     * @returns {Number} The maximum number of bonds of this atom.
     */
    getMaxBonds() {
      return _Atom.maxBonds[this.element];
    }
    /**
     * A map mapping element symbols to their maximum bonds.
     */
    static get maxBonds() {
      return {
        H: 1,
        C: 4,
        N: 3,
        O: 2,
        P: 3,
        S: 2,
        B: 3,
        F: 1,
        I: 1,
        Cl: 1,
        Br: 1
      };
    }
    /**
     * A map mapping element symbols to the atomic number.
     */
    static get atomicNumbers() {
      return {
        H: 1,
        He: 2,
        Li: 3,
        Be: 4,
        B: 5,
        b: 5,
        C: 6,
        c: 6,
        N: 7,
        n: 7,
        O: 8,
        o: 8,
        F: 9,
        Ne: 10,
        Na: 11,
        Mg: 12,
        Al: 13,
        Si: 14,
        P: 15,
        p: 15,
        S: 16,
        s: 16,
        Cl: 17,
        Ar: 18,
        K: 19,
        Ca: 20,
        Sc: 21,
        Ti: 22,
        V: 23,
        Cr: 24,
        Mn: 25,
        Fe: 26,
        Co: 27,
        Ni: 28,
        Cu: 29,
        Zn: 30,
        Ga: 31,
        Ge: 32,
        As: 33,
        Se: 34,
        Br: 35,
        Kr: 36,
        Rb: 37,
        Sr: 38,
        Y: 39,
        Zr: 40,
        Nb: 41,
        Mo: 42,
        Tc: 43,
        Ru: 44,
        Rh: 45,
        Pd: 46,
        Ag: 47,
        Cd: 48,
        In: 49,
        Sn: 50,
        Sb: 51,
        Te: 52,
        I: 53,
        Xe: 54,
        Cs: 55,
        Ba: 56,
        La: 57,
        Ce: 58,
        Pr: 59,
        Nd: 60,
        Pm: 61,
        Sm: 62,
        Eu: 63,
        Gd: 64,
        Tb: 65,
        Dy: 66,
        Ho: 67,
        Er: 68,
        Tm: 69,
        Yb: 70,
        Lu: 71,
        Hf: 72,
        Ta: 73,
        W: 74,
        Re: 75,
        Os: 76,
        Ir: 77,
        Pt: 78,
        Au: 79,
        Hg: 80,
        Tl: 81,
        Pb: 82,
        Bi: 83,
        Po: 84,
        At: 85,
        Rn: 86,
        Fr: 87,
        Ra: 88,
        Ac: 89,
        Th: 90,
        Pa: 91,
        U: 92,
        Np: 93,
        Pu: 94,
        Am: 95,
        Cm: 96,
        Bk: 97,
        Cf: 98,
        Es: 99,
        Fm: 100,
        Md: 101,
        No: 102,
        Lr: 103,
        Rf: 104,
        Db: 105,
        Sg: 106,
        Bh: 107,
        Hs: 108,
        Mt: 109,
        Ds: 110,
        Rg: 111,
        Cn: 112,
        Uut: 113,
        Uuq: 114,
        Uup: 115,
        Uuh: 116,
        Uus: 117,
        Uuo: 118
      };
    }
  };

  // node_modules/smiles-drawer/src/Vector2.js
  var Vector2 = class _Vector2 {
    /**
     * The constructor of the class Vector2.
     *
     * @param {(Number|Vector2)} x The initial x coordinate value or, if the single argument, a Vector2 object.
     * @param {Number} y The initial y coordinate value.
     */
    constructor(x, y) {
      if (arguments.length == 0) {
        this.x = 0;
        this.y = 0;
      } else if (x instanceof _Vector2) {
        this.x = x.x;
        this.y = x.y;
      } else {
        this.x = x;
        this.y = y;
      }
    }
    /**
     * Clones this vector and returns the clone.
     *
     * @returns {Vector2} The clone of this vector.
     */
    clone() {
      return new _Vector2(this.x, this.y);
    }
    /**
     * Returns a string representation of this vector.
     *
     * @returns {String} A string representation of this vector.
     */
    toString() {
      return "(" + this.x + "," + this.y + ")";
    }
    /**
     * Add the x and y coordinate values of a vector to the x and y coordinate values of this vector.
     *
     * @param {Vector2} vec Another vector.
     * @returns {Vector2} Returns itself.
     */
    add(vec) {
      this.x += vec.x;
      this.y += vec.y;
      return this;
    }
    /**
     * Subtract the x and y coordinate values of a vector from the x and y coordinate values of this vector.
     *
     * @param {Vector2} vec Another vector.
     * @returns {Vector2} Returns itself.
     */
    subtract(vec) {
      this.x -= vec.x;
      this.y -= vec.y;
      return this;
    }
    /**
     * Divide the x and y coordinate values of this vector by a scalar.
     *
     * @param {Number} scalar The scalar.
     * @returns {Vector2} Returns itself.
     */
    divide(scalar) {
      this.x /= scalar;
      this.y /= scalar;
      return this;
    }
    /**
     * Multiply the x and y coordinate values of this vector by the values of another vector.
     *
     * @param {Vector2} v A vector.
     * @returns {Vector2} Returns itself.
     */
    multiply(v) {
      this.x *= v.x;
      this.y *= v.y;
      return this;
    }
    /**
     * Multiply the x and y coordinate values of this vector by a scalar.
     *
     * @param {Number} scalar The scalar.
     * @returns {Vector2} Returns itself.
     */
    multiplyScalar(scalar) {
      this.x *= scalar;
      this.y *= scalar;
      return this;
    }
    /**
     * Inverts this vector. Same as multiply(-1.0).
     *
     * @returns {Vector2} Returns itself.
     */
    invert() {
      this.x = -this.x;
      this.y = -this.y;
      return this;
    }
    /**
     * Returns the angle of this vector in relation to the coordinate system.
     *
     * @returns {Number} The angle in radians.
     */
    angle() {
      return Math.atan2(this.y, this.x);
    }
    /**
     * Returns the euclidean distance between this vector and another vector.
     *
     * @param {Vector2} vec A vector.
     * @returns {Number} The euclidean distance between the two vectors.
     */
    distance(vec) {
      return Math.sqrt((vec.x - this.x) * (vec.x - this.x) + (vec.y - this.y) * (vec.y - this.y));
    }
    /**
     * Returns the squared euclidean distance between this vector and another vector. When only the relative distances of a set of vectors are needed, this is is less expensive than using distance(vec).
     *
     * @param {Vector2} vec Another vector.
     * @returns {Number} The squared euclidean distance of the two vectors.
     */
    distanceSq(vec) {
      return (vec.x - this.x) * (vec.x - this.x) + (vec.y - this.y) * (vec.y - this.y);
    }
    /**
     * Checks whether or not this vector is in a clockwise or counter-clockwise rotational direction compared to another vector in relation to the coordinate system.
     *
     * @param {Vector2} vec Another vector.
     * @returns {Number} Returns -1, 0 or 1 if the vector supplied as an argument is clockwise, neutral or counter-clockwise respectively to this vector in relation to the coordinate system.
     */
    clockwise(vec) {
      let a = this.y * vec.x;
      let b = this.x * vec.y;
      if (a > b) {
        return -1;
      } else if (a === b) {
        return 0;
      }
      return 1;
    }
    /**
     * Checks whether or not this vector is in a clockwise or counter-clockwise rotational direction compared to another vector in relation to an arbitrary third vector.
     *
     * @param {Vector2} center The central vector.
     * @param {Vector2} vec Another vector.
     * @returns {Number} Returns -1, 0 or 1 if the vector supplied as an argument is clockwise, neutral or counter-clockwise respectively to this vector in relation to an arbitrary third vector.
     */
    relativeClockwise(center, vec) {
      let a = (this.y - center.y) * (vec.x - center.x);
      let b = (this.x - center.x) * (vec.y - center.y);
      if (a > b) {
        return -1;
      } else if (a === b) {
        return 0;
      }
      return 1;
    }
    /**
     * Rotates this vector by a given number of radians around the origin of the coordinate system.
     *
     * @param {Number} angle The angle in radians to rotate the vector.
     * @returns {Vector2} Returns itself.
     */
    rotate(angle) {
      let tmp = new _Vector2(0, 0);
      let cosAngle = Math.cos(angle);
      let sinAngle = Math.sin(angle);
      tmp.x = this.x * cosAngle - this.y * sinAngle;
      tmp.y = this.x * sinAngle + this.y * cosAngle;
      this.x = tmp.x;
      this.y = tmp.y;
      return this;
    }
    /**
     * Rotates this vector around another vector.
     *
     * @param {Number} angle The angle in radians to rotate the vector.
     * @param {Vector2} vec The vector which is used as the rotational center.
     * @returns {Vector2} Returns itself.
     */
    rotateAround(angle, vec) {
      let s = Math.sin(angle);
      let c = Math.cos(angle);
      this.x -= vec.x;
      this.y -= vec.y;
      let x = this.x * c - this.y * s;
      let y = this.x * s + this.y * c;
      this.x = x + vec.x;
      this.y = y + vec.y;
      return this;
    }
    /**
     * Rotate a vector around a given center to the same angle as another vector (so that the two vectors and the center are in a line, with both vectors on one side of the center), keeps the distance from this vector to the center.
     *
     * @param {Vector2} vec The vector to rotate this vector to.
     * @param {Vector2} center The rotational center.
     * @param {Number} [offsetAngle=0.0] An additional amount of radians to rotate the vector.
     * @returns {Vector2} Returns itself.
     */
    rotateTo(vec, center, offsetAngle = 0) {
      this.x += 1e-3;
      this.y -= 1e-3;
      let a = _Vector2.subtract(this, center);
      let b = _Vector2.subtract(vec, center);
      let angle = _Vector2.angle(b, a);
      this.rotateAround(angle + offsetAngle, center);
      return this;
    }
    /**
     * Rotates the vector away from a specified vector around a center.
     *
     * @param {Vector2} vec The vector this one is rotated away from.
     * @param {Vector2} center The rotational center.
     * @param {Number} angle The angle by which to rotate.
     */
    rotateAwayFrom(vec, center, angle) {
      this.rotateAround(angle, center);
      let distSqA = this.distanceSq(vec);
      this.rotateAround(-2 * angle, center);
      let distSqB = this.distanceSq(vec);
      if (distSqB < distSqA) {
        this.rotateAround(2 * angle, center);
      }
    }
    /**
     * Returns the angle in radians used to rotate this vector away from a given vector.
     *
     * @param {Vector2} vec The vector this one is rotated away from.
     * @param {Vector2} center The rotational center.
     * @param {Number} angle The angle by which to rotate.
     * @returns {Number} The angle in radians.
     */
    getRotateAwayFromAngle(vec, center, angle) {
      let tmp = this.clone();
      tmp.rotateAround(angle, center);
      let distSqA = tmp.distanceSq(vec);
      tmp.rotateAround(-2 * angle, center);
      let distSqB = tmp.distanceSq(vec);
      if (distSqB < distSqA) {
        return angle;
      } else {
        return -angle;
      }
    }
    /**
     * Returns the angle in radians used to rotate this vector towards a given vector.
     *
     * @param {Vector2} vec The vector this one is rotated towards to.
     * @param {Vector2} center The rotational center.
     * @param {Number} angle The angle by which to rotate.
     * @returns {Number} The angle in radians.
     */
    getRotateTowardsAngle(vec, center, angle) {
      let tmp = this.clone();
      tmp.rotateAround(angle, center);
      let distSqA = tmp.distanceSq(vec);
      tmp.rotateAround(-2 * angle, center);
      let distSqB = tmp.distanceSq(vec);
      if (distSqB > distSqA) {
        return angle;
      } else {
        return -angle;
      }
    }
    /**
     * Gets the angles between this vector and another vector around a common center of rotation.
     *
     * @param {Vector2} vec Another vector.
     * @param {Vector2} center The center of rotation.
     * @returns {Number} The angle between this vector and another vector around a center of rotation in radians.
     */
    getRotateToAngle(vec, center) {
      let a = _Vector2.subtract(this, center);
      let b = _Vector2.subtract(vec, center);
      let angle = _Vector2.angle(b, a);
      return Number.isNaN(angle) ? 0 : angle;
    }
    /**
     * Checks whether a vector lies within a polygon spanned by a set of vectors.
     *
     * @param {Vector2[]} polygon An array of vectors spanning the polygon.
     * @returns {Boolean} A boolean indicating whether or not this vector is within a polygon.
     */
    isInPolygon(polygon) {
      let inside = false;
      for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
        const a = polygon[i];
        const b = polygon[j];
        if (a.y > this.y != b.y > this.y && this.x < (b.x - a.x) * (this.y - a.y) / (b.y - a.y) + a.x) {
          inside = !inside;
        }
      }
      return inside;
    }
    /**
     * Returns the length of this vector.
     *
     * @returns {Number} The length of this vector.
     */
    length() {
      return Math.sqrt(this.x * this.x + this.y * this.y);
    }
    /**
     * Returns the square of the length of this vector.
     *
     * @returns {Number} The square of the length of this vector.
     */
    lengthSq() {
      return this.x * this.x + this.y * this.y;
    }
    /**
     * Normalizes this vector.
     *
     * @returns {Vector2} Returns itself.
     */
    normalize() {
      this.divide(this.length());
      return this;
    }
    /**
     * Returns a normalized copy of this vector.
     *
     * @returns {Vector2} A normalized copy of this vector.
     */
    normalized() {
      return _Vector2.divideScalar(this, this.length());
    }
    /**
     * Calculates which side of a line spanned by two vectors this vector is.
     *
     * @param {Vector2} vecA A vector.
     * @param {Vector2} vecB A vector.
     * @returns {Number} A number indicating the side of this vector, given a line spanned by two other vectors.
     */
    whichSide(vecA, vecB) {
      return (this.x - vecA.x) * (vecB.y - vecA.y) - (this.y - vecA.y) * (vecB.x - vecA.x);
    }
    /**
     * Checks whether or not this vector is on the same side of a line spanned by two vectors as another vector.
     *
     * @param {Vector2} vecA A vector spanning the line.
     * @param {Vector2} vecB A vector spanning the line.
     * @param {Vector2} vecC A vector to check whether or not it is on the same side as this vector.
     * @returns {Boolean} Returns a boolean indicating whether or not this vector is on the same side as another vector.
     */
    sameSideAs(vecA, vecB, vecC) {
      let d = this.whichSide(vecA, vecB);
      let dRef = vecC.whichSide(vecA, vecB);
      return d < 0 && dRef < 0 || d == 0 && dRef == 0 || d > 0 && dRef > 0;
    }
    /**
     * Adds two vectors and returns the result as a new vector.
     *
     * @static
     * @param {Vector2} vecA A summand.
     * @param {Vector2} vecB A summand.
     * @returns {Vector2} Returns the sum of two vectors.
     */
    static add(vecA, vecB) {
      return new _Vector2(vecA.x + vecB.x, vecA.y + vecB.y);
    }
    /**
     * Subtracts one vector from another and returns the result as a new vector.
     *
     * @static
     * @param {Vector2} vecA The minuend.
     * @param {Vector2} vecB The subtrahend.
     * @returns {Vector2} Returns the difference of two vectors.
     */
    static subtract(vecA, vecB) {
      return new _Vector2(vecA.x - vecB.x, vecA.y - vecB.y);
    }
    /**
     * Multiplies two vectors (value by value) and returns the result.
     *
     * @static
     * @param {Vector2} vecA A vector.
     * @param {Vector2} vecB A vector.
     * @returns {Vector2} Returns the product of two vectors.
     */
    static multiply(vecA, vecB) {
      return new _Vector2(vecA.x * vecB.x, vecA.y * vecB.y);
    }
    /**
     * Multiplies two vectors (value by value) and returns the result.
     *
     * @static
     * @param {Vector2} vec A vector.
     * @param {Number} scalar A scalar.
     * @returns {Vector2} Returns the product of two vectors.
     */
    static multiplyScalar(vec, scalar) {
      return new _Vector2(vec.x, vec.y).multiplyScalar(scalar);
    }
    /**
     * Returns the midpoint of a line spanned by two vectors.
     *
     * @static
     * @param {Vector2} vecA A vector spanning the line.
     * @param {Vector2} vecB A vector spanning the line.
     * @returns {Vector2} The midpoint of the line spanned by two vectors.
     */
    static midpoint(vecA, vecB) {
      return new _Vector2((vecA.x + vecB.x) / 2, (vecA.y + vecB.y) / 2);
    }
    /**
     * Returns the normals of a line spanned by two vectors.
     *
     * @static
     * @param {Vector2} vecA A vector spanning the line.
     * @param {Vector2} vecB A vector spanning the line.
     * @returns {Vector2[]} An array containing the two normals, each represented by a vector.
     */
    static normals(vecA, vecB) {
      let delta = _Vector2.subtract(vecB, vecA);
      return [
        new _Vector2(-delta.y, delta.x),
        new _Vector2(delta.y, -delta.x)
      ];
    }
    /**
     * Returns the unit (normalized normal) vectors of a line spanned by two vectors.
     *
     * @static
     * @param {Vector2} vecA A vector spanning the line.
     * @param {Vector2} vecB A vector spanning the line.
     * @returns {Vector2[]} An array containing the two unit vectors.
     */
    static units(vecA, vecB) {
      let delta = _Vector2.subtract(vecB, vecA);
      return [
        new _Vector2(-delta.y, delta.x).normalize(),
        new _Vector2(delta.y, -delta.x).normalize()
      ];
    }
    /**
     * Divides a vector by another vector and returns the result as new vector.
     *
     * @static
     * @param {Vector2} vecA The dividend.
     * @param {Vector2} vecB The divisor.
     * @returns {Vector2} The fraction of the two vectors.
     */
    static divide(vecA, vecB) {
      return new _Vector2(vecA.x / vecB.x, vecA.y / vecB.y);
    }
    /**
     * Divides a vector by a scalar and returns the result as new vector.
     *
     * @static
     * @param {Vector2} vecA The dividend.
     * @param {Number} s The scalar.
     * @returns {Vector2} The fraction of the two vectors.
     */
    static divideScalar(vecA, s) {
      return new _Vector2(vecA.x / s, vecA.y / s);
    }
    /**
     * Returns the dot product of two vectors.
     *
     * @static
     * @param {Vector2} vecA A vector.
     * @param {Vector2} vecB A vector.
     * @returns {Number} The dot product of two vectors.
     */
    static dot(vecA, vecB) {
      return vecA.x * vecB.x + vecA.y * vecB.y;
    }
    /**
     * Returns the angle between two vectors.
     *
     * @static
     * @param {Vector2} vecA A vector.
     * @param {Vector2} vecB A vector.
     * @returns {Number} The angle between two vectors in radians.
     */
    static angle(vecA, vecB) {
      let dot = _Vector2.dot(vecA, vecB);
      return Math.acos(dot / (vecA.length() * vecB.length()));
    }
    /**
     * Returns the angle between two vectors based on a third vector in between.
     *
     * @static
     * @param {Vector2} vecA A vector.
     * @param {Vector2} vecB A (central) vector.
     * @param {Vector2} vecC A vector.
     * @returns {Number} The angle in radians.
     */
    static threePointangle(vecA, vecB, vecC) {
      let ab = _Vector2.subtract(vecB, vecA);
      let bc = _Vector2.subtract(vecC, vecB);
      let abLength = vecA.distance(vecB);
      let bcLength = vecB.distance(vecC);
      return Math.acos(_Vector2.dot(ab, bc) / (abLength * bcLength));
    }
    /**
     * Returns the scalar projection of a vector on another vector.
     *
     * @static
     * @param {Vector2} vecA The vector to be projected.
     * @param {Vector2} vecB The vector to be projection upon.
     * @returns {Number} The scalar component.
     */
    static scalarProjection(vecA, vecB) {
      let unit = vecB.normalized();
      return _Vector2.dot(vecA, unit);
    }
    /**
     * Returns the average vector (normalized) of the input vectors.
     *
     * @static
     * @param {Array} vecs An array containing vectors.
     * @returns {Vector2} The resulting vector (normalized).
     */
    static averageDirection(vecs) {
      let avg = new _Vector2(0, 0);
      for (let i = 0; i < vecs.length; i++) {
        let vec = vecs[i];
        avg.add(vec);
      }
      return avg.normalize();
    }
  };

  // node_modules/smiles-drawer/src/Line.js
  var Line = class _Line {
    /**
     * The constructor for the class Line.
     *
     * @param {Vector2} [from=new Vector2(0, 0)] A vector marking the beginning of the line.
     * @param {Vector2} [to=new Vector2(0, 0)] A vector marking the end of the line.
     * @param {string} [elementFrom=null] A one-letter representation of the element associated with the vector marking the beginning of the line.
     * @param {string} [elementTo=null] A one-letter representation of the element associated with the vector marking the end of the line.
     * @param {Boolean} [chiralFrom=false] Whether or not the from atom is a chiral center.
     * @param {Boolean} [chiralTo=false] Whether or not the to atom is a chiral center.
     */
    constructor(from = new Vector2(0, 0), to = new Vector2(0, 0), elementFrom = null, elementTo = null, chiralFrom = false, chiralTo = false) {
      this.from = from;
      this.to = to;
      this.elementFrom = elementFrom;
      this.elementTo = elementTo;
      this.chiralFrom = chiralFrom;
      this.chiralTo = chiralTo;
    }
    /**
     * Clones this line and returns the clone.
     *
     * @returns {Line} A clone of this line.
     */
    clone() {
      return new _Line(this.from.clone(), this.to.clone(), this.elementFrom, this.elementTo);
    }
    /**
     * Returns the length of this line.
     *
     * @returns {Number} The length of this line.
     */
    getLength() {
      const dx = this.to.x - this.from.x;
      const dy = this.to.y - this.from.y;
      return Math.sqrt(dx * dx + dy * dy);
    }
    /**
     * Returns the angle of the line in relation to the coordinate system (the x-axis).
     *
     * @returns {Number} The angle in radians.
     */
    getAngle() {
      let diff = Vector2.subtract(this.getRightVector(), this.getLeftVector());
      return diff.angle();
    }
    /**
     * Returns the right vector (the vector with the larger x value).
     *
     * @returns {Vector2} The right vector.
     */
    getRightVector() {
      if (this.from.x < this.to.x) {
        return this.to;
      } else {
        return this.from;
      }
    }
    /**
     * Returns the left vector (the vector with the smaller x value).
     *
     * @returns {Vector2} The left vector.
     */
    getLeftVector() {
      if (this.from.x < this.to.x) {
        return this.from;
      } else {
        return this.to;
      }
    }
    /**
     * Returns the element associated with the right vector (the vector with the larger x value).
     *
     * @returns {String} The element associated with the right vector.
     */
    getRightElement() {
      if (this.from.x < this.to.x) {
        return this.elementTo;
      } else {
        return this.elementFrom;
      }
    }
    /**
     * Returns the element associated with the left vector (the vector with the smaller x value).
     *
     * @returns {String} The element associated with the left vector.
     */
    getLeftElement() {
      if (this.from.x < this.to.x) {
        return this.elementFrom;
      } else {
        return this.elementTo;
      }
    }
    /**
     * Returns whether or not the atom associated with the right vector (the vector with the larger x value) is a chiral center.
     *
     * @returns {Boolean} Whether or not the atom associated with the right vector is a chiral center.
     */
    getRightChiral() {
      if (this.from.x < this.to.x) {
        return this.chiralTo;
      } else {
        return this.chiralFrom;
      }
    }
    /**
     * Returns whether or not the atom associated with the left vector (the vector with the smaller x value) is a chiral center.
     *
     * @returns {Boolean} Whether or not the atom  associated with the left vector is a chiral center.
     */
    getLeftChiral() {
      if (this.from.x < this.to.x) {
        return this.chiralFrom;
      } else {
        return this.chiralTo;
      }
    }
    /**
     * Set the value of the right vector.
     *
     * @param {Number} x The x value.
     * @param {Number} y The y value.
     * @returns {Line} This line.
     */
    setRightVector(x, y) {
      if (this.from.x < this.to.x) {
        this.to.x = x;
        this.to.y = y;
      } else {
        this.from.x = x;
        this.from.y = y;
      }
      return this;
    }
    /**
     * Set the value of the left vector.
     *
     * @param {Number} x The x value.
     * @param {Number} y The y value.
     * @returns {Line} This line.
     */
    setLeftVector(x, y) {
      if (this.from.x < this.to.x) {
        this.from.x = x;
        this.from.y = y;
      } else {
        this.to.x = x;
        this.to.y = y;
      }
      return this;
    }
    /**
     * Rotates this line to be aligned with the x-axis. The center of rotation is the left vector.
     *
     * @returns {Line} This line.
     */
    rotateToXAxis() {
      let left = this.getLeftVector();
      this.setRightVector(left.x + this.getLength(), left.y);
      return this;
    }
    /**
     * Rotate the line by a given value (in radians). The center of rotation is the left vector.
     *
     * @param {Number} theta The angle (in radians) to rotate the line.
     * @returns {Line} This line.
     */
    rotate(theta) {
      let l = this.getLeftVector();
      let r = this.getRightVector();
      let sinTheta = Math.sin(theta);
      let cosTheta = Math.cos(theta);
      let x = cosTheta * (r.x - l.x) - sinTheta * (r.y - l.y) + l.x;
      let y = sinTheta * (r.x - l.x) - cosTheta * (r.y - l.y) + l.y;
      this.setRightVector(x, y);
      return this;
    }
    /**
     * Shortens this line from the "from" direction by a given value (in pixels).
     *
     * @param {Number} by The length in pixels to shorten the vector by.
     * @returns {Line} This line.
     */
    shortenFrom(by) {
      let f = Vector2.subtract(this.to, this.from);
      f.normalize();
      f.multiplyScalar(by);
      this.from.add(f);
      return this;
    }
    /**
     * Shortens this line from the "to" direction by a given value (in pixels).
     *
     * @param {Number} by The length in pixels to shorten the vector by.
     * @returns {Line} This line.
     */
    shortenTo(by) {
      let f = Vector2.subtract(this.from, this.to);
      f.normalize();
      f.multiplyScalar(by);
      this.to.add(f);
      return this;
    }
    /**
     * Shorten the right side.
     *
     * @param {Number} by The length in pixels to shorten the vector by.
     * @returns {Line} Returns itself.
     */
    shortenRight(by) {
      if (this.from.x < this.to.x) {
        this.shortenTo(by);
      } else {
        this.shortenFrom(by);
      }
      return this;
    }
    /**
     * Shorten the left side.
     *
     * @param {Number} by The length in pixels to shorten the vector by.
     * @returns {Line} Returns itself.
     */
    shortenLeft(by) {
      if (this.from.x < this.to.x) {
        this.shortenFrom(by);
      } else {
        this.shortenTo(by);
      }
      return this;
    }
    /**
     * Shortens this line from both directions by a given value (in pixels).
     *
     * @param {Number} by The length in pixels to shorten the vector by.
     * @returns {Line} This line.
     */
    shorten(by) {
      let f = Vector2.subtract(this.from, this.to);
      f.normalize();
      f.multiplyScalar(by / 2);
      this.to.add(f);
      this.from.subtract(f);
      return this;
    }
  };

  // node_modules/smiles-drawer/src/MathHelper.js
  var MathHelper = class _MathHelper {
    /**
     * Rounds a value to a given number of decimals.
     *
     * @static
     * @param {Number} value A number.
     * @param {Number} decimals The number of decimals.
     * @returns {Number} A number rounded to a given number of decimals.
     */
    static round(value, decimals) {
      if (decimals) {
        const pow12 = Math.pow(10, decimals);
        return Math.round(value * pow12) / pow12;
      } else {
        return Math.round(value);
      }
    }
    /**
     * Returns the means of the angles contained in an array. In radians.
     *
     * @static
     * @param {Number[]} arr An array containing angles (in radians).
     * @returns {Number} The mean angle in radians.
     */
    static meanAngle(arr) {
      let sin5 = 0;
      let cos6 = 0;
      for (let i = 0; i < arr.length; i++) {
        sin5 += Math.sin(arr[i]);
        cos6 += Math.cos(arr[i]);
      }
      return Math.atan2(sin5 / arr.length, cos6 / arr.length);
    }
    /**
     * Returns the inner angle of a n-sided regular polygon.
     *
     * @static
     * @param {Number} n Number of sides of a regular polygon.
     * @returns {Number} The inner angle of a given regular polygon.
     */
    static innerAngle(n) {
      return _MathHelper.toRad((n - 2) * 180 / n);
    }
    /**
     * Returns the circumradius of a n-sided regular polygon with a given side-length.
     *
     * @static
     * @param {Number} s The side length of the regular polygon.
     * @param {Number} n The number of sides.
     * @returns {Number} The circumradius of the regular polygon.
     */
    static polyCircumradius(s, n) {
      return s / (2 * Math.sin(Math.PI / n));
    }
    /**
     * Returns the apothem of a regular n-sided polygon based on its radius.
     *
     * @static
     * @param {Number} r The radius.
     * @param {Number} n The number of edges of the regular polygon.
     * @returns {Number} The apothem of a n-sided polygon based on its radius.
     */
    static apothem(r, n) {
      return r * Math.cos(Math.PI / n);
    }
    static apothemFromSideLength(s, n) {
      let r = _MathHelper.polyCircumradius(s, n);
      return _MathHelper.apothem(r, n);
    }
    /**
     * The central angle of a n-sided regular polygon. In radians.
     *
     * @static
     * @param {Number} n The number of sides of the regular polygon.
     * @returns {Number} The central angle of the n-sided polygon in radians.
     */
    static centralAngle(n) {
      return _MathHelper.toRad(360 / n);
    }
    /**
     * Convertes radians to degrees.
     *
     * @static
     * @param {Number} rad An angle in radians.
     * @returns {Number} The angle in degrees.
     */
    static toDeg(rad) {
      return rad * _MathHelper.degFactor;
    }
    /**
     * Converts degrees to radians.
     *
     * @static
     * @param {Number} deg An angle in degrees.
     * @returns {Number} The angle in radians.
     */
    static toRad(deg) {
      return deg * _MathHelper.radFactor;
    }
    /**
     * Returns the parity of the permutation (1 or -1)
     * @param {(Array|Uint8Array)} arr An array containing the permutation.
     * @returns {Number} The parity of the permutation (1 or -1), where 1 means even and -1 means odd.
     */
    static parityOfPermutation(arr) {
      let visited = new Uint8Array(arr.length);
      let evenLengthCycleCount = 0;
      let traverseCycle = function(i, cycleLength = 0) {
        if (visited[i] === 1) {
          return cycleLength;
        }
        cycleLength++;
        visited[i] = 1;
        return traverseCycle(arr[i], cycleLength);
      };
      for (let i = 0; i < arr.length; i++) {
        if (visited[i] === 1) {
          continue;
        }
        let cycleLength = traverseCycle(i);
        evenLengthCycleCount += 1 - cycleLength % 2;
      }
      return evenLengthCycleCount % 2 ? -1 : 1;
    }
    /** The factor to convert degrees to radians. */
    static get radFactor() {
      return Math.PI / 180;
    }
    /** The factor to convert radians to degrees. */
    static get degFactor() {
      return 180 / Math.PI;
    }
    /** Two times PI. */
    static get twoPI() {
      return 2 * Math.PI;
    }
  };

  // node_modules/smiles-drawer/src/Vertex.js
  var Vertex = class _Vertex {
    /**
     * The constructor for the class Vertex.
     *
     * @param {Atom} value The value associated with this vertex.
     * @param {Number} [x=0] The initial x coordinate of the positional vector of this vertex.
     * @param {Number} [y=0] The initial y coordinate of the positional vector of this vertex.
     */
    constructor(value, x = 0, y = 0) {
      this.id = null;
      this.value = value;
      this.position = new Vector2(x ? x : 0, y ? y : 0);
      this.previousPosition = new Vector2(0, 0);
      this.parentVertexId = null;
      this.children = [];
      this.spanningTreeChildren = [];
      this.edges = [];
      this.positioned = false;
      this.angle = null;
      this.dir = 1;
      this.neighbourCount = 0;
      this.neighbours = [];
      this.neighbouringElements = [];
      this.forcePositioned = false;
    }
    /**
     * Set the 2D coordinates of the vertex.
     *
     * @param {Number} x The x component of the coordinates.
     * @param {Number} y The y component of the coordinates.
     *
     */
    setPosition(x, y) {
      this.position.x = x;
      this.position.y = y;
    }
    /**
     * Set the 2D coordinates of the vertex from a Vector2.
     *
     * @param {Vector2} v A 2D vector.
     *
     */
    setPositionFromVector(v) {
      this.position.x = v.x;
      this.position.y = v.y;
    }
    /**
     * Add a child vertex id to this vertex.
     * @param {Number} vertexId The id of a vertex to be added as a child to this vertex.
     */
    addChild(vertexId) {
      this.children.push(vertexId);
      this.neighbours.push(vertexId);
      this.neighbourCount++;
    }
    /**
     * Add a child vertex id to this vertex as the second child of the neighbours array,
     * except this vertex is the first vertex of the SMILE string, then it is added as the first.
     * This is used to get the correct ordering of neighbours for parity calculations.
     * If a hydrogen is implicitly attached to the chiral center, insert as the third child.
     * @param {Number} vertexId The id of a vertex to be added as a child to this vertex.
     * @param {Number} ringbondIndex The index of the ringbond.
     */
    addRingbondChild(vertexId, ringbondIndex) {
      this.children.push(vertexId);
      if (this.value.bracket) {
        let index = 1;
        if (this.id === 0 && this.value.bracket.hcount === 0) {
          index = 0;
        }
        if (this.value.bracket.hcount === 1 && ringbondIndex === 0) {
          index = 2;
        }
        if (this.value.bracket.hcount === 1 && ringbondIndex === 1) {
          if (this.neighbours.length < 3) {
            index = 2;
          } else {
            index = 3;
          }
        }
        if (this.value.bracket.hcount === null && ringbondIndex === 0) {
          index = 1;
        }
        if (this.value.bracket.hcount === null && ringbondIndex === 1) {
          if (this.neighbours.length < 3) {
            index = 1;
          } else {
            index = 2;
          }
        }
        this.neighbours.splice(index, 0, vertexId);
      } else {
        this.neighbours.push(vertexId);
      }
      this.neighbourCount++;
    }
    /**
     * Set the vertex id of the parent.
     *
     * @param {Number} parentVertexId The parents vertex id.
     */
    setParentVertexId(parentVertexId) {
      this.neighbourCount++;
      this.parentVertexId = parentVertexId;
      this.neighbours.push(parentVertexId);
    }
    /**
     * Returns true if this vertex is terminal (has no parent or child vertices), otherwise returns false. Always returns true if associated value has property hasAttachedPseudoElements set to true.
     *
     * @returns {Boolean} A boolean indicating whether or not this vertex is terminal.
     */
    isTerminal() {
      if (this.value.hasAttachedPseudoElements) {
        return true;
      }
      return this.parentVertexId === null && this.children.length < 2 || this.children.length === 0;
    }
    /**
     * Clones this vertex and returns the clone.
     *
     * @returns {Vertex} A clone of this vertex.
     */
    clone() {
      let clone = new _Vertex(this.value, this.position.x, this.position.y);
      clone.id = this.id;
      clone.previousPosition = new Vector2(this.previousPosition.x, this.previousPosition.y);
      clone.parentVertexId = this.parentVertexId;
      clone.children = ArrayHelper.clone(this.children);
      clone.spanningTreeChildren = ArrayHelper.clone(this.spanningTreeChildren);
      clone.edges = ArrayHelper.clone(this.edges);
      clone.positioned = this.positioned;
      clone.angle = this.angle;
      clone.forcePositioned = this.forcePositioned;
      return clone;
    }
    /**
     * Returns true if this vertex and the supplied vertex both have the same id, else returns false.
     *
     * @param {Vertex} vertex The vertex to check.
     * @returns {Boolean} A boolean indicating whether or not the two vertices have the same id.
     */
    equals(vertex) {
      return this.id === vertex.id;
    }
    /**
     * Returns the angle of this vertexes positional vector. If a reference vector is supplied in relations to this vector, else in relations to the coordinate system.
     *
     * @param {Vector2} [referenceVector=null] - The reference vector.
     * @param {Boolean} [returnAsDegrees=false] - If true, returns angle in degrees, else in radians.
     * @returns {Number} The angle of this vertex.
     */
    getAngle(referenceVector = null, returnAsDegrees = false) {
      let u = null;
      if (!referenceVector) {
        u = Vector2.subtract(this.position, this.previousPosition);
      } else {
        u = Vector2.subtract(this.position, referenceVector);
      }
      if (returnAsDegrees) {
        return MathHelper.toDeg(u.angle());
      }
      return u.angle();
    }
    /**
     * Returns the suggested text direction when text is added at the position of this vertex.
     *
     * @param {Vertex[]} vertices The array of vertices for the current molecule.
     * @param {Boolean} onlyHorizontal In case the text direction should be limited to either left or right.
     * @returns {String} The suggested direction of the text.
     */
    getTextDirection(vertices, onlyHorizontal = false) {
      let neighbours = this.getDrawnNeighbours(vertices);
      let angles = [];
      if (vertices.length === 1) {
        return "right";
      }
      for (let i = 0; i < neighbours.length; i++) {
        angles.push(this.getAngle(vertices[neighbours[i]].position));
      }
      let textAngle = MathHelper.meanAngle(angles);
      if (this.isTerminal() || onlyHorizontal) {
        if (Math.round(textAngle * 100) / 100 === 1.57) {
          textAngle = textAngle - 0.2;
        }
        textAngle = Math.round(Math.round(textAngle / Math.PI) * Math.PI);
      } else {
        let halfPi = Math.PI / 2;
        textAngle = Math.round(Math.round(textAngle / halfPi) * halfPi);
      }
      if (textAngle === 2) {
        return "down";
      } else if (textAngle === -2) {
        return "up";
      } else if (textAngle === 0) {
        return "right";
      } else if (textAngle === 3 || textAngle === -3) {
        return "left";
      } else {
        return "down";
      }
    }
    /**
     * Returns an array of ids of neighbouring vertices.
     *
     * @param {Number} [vertexId=null] If a value is supplied, the vertex with this id is excluded from the returned indices.
     * @returns {Number[]} An array containing the ids of neighbouring vertices.
     */
    getNeighbours(vertexId = null) {
      if (vertexId === null) {
        return this.neighbours.slice();
      }
      let arr = [];
      for (let i = 0; i < this.neighbours.length; i++) {
        if (this.neighbours[i] !== vertexId) {
          arr.push(this.neighbours[i]);
        }
      }
      return arr;
    }
    /**
     * Returns an array of ids of neighbouring vertices that will be drawn (vertex.value.isDrawn === true).
     *
     * @param {Vertex[]} vertices An array containing the vertices associated with the current molecule.
     * @returns {Number[]} An array containing the ids of neighbouring vertices that will be drawn.
     */
    getDrawnNeighbours(vertices) {
      let arr = [];
      for (let i = 0; i < this.neighbours.length; i++) {
        if (vertices[this.neighbours[i]].value.isDrawn) {
          arr.push(this.neighbours[i]);
        }
      }
      return arr;
    }
    /**
     * Returns the number of neighbours of this vertex.
     *
     * @returns {Number} The number of neighbours.
     */
    getNeighbourCount() {
      return this.neighbourCount;
    }
    /**
     * Returns a list of ids of vertices neighbouring this one in the original spanning tree, excluding the ringbond connections.
     *
     * @param {Number} [vertexId=null] If supplied, the vertex with this id is excluded from the array returned.
     * @returns {Number[]} An array containing the ids of the neighbouring vertices.
     */
    getSpanningTreeNeighbours(vertexId = null) {
      let neighbours = [];
      for (let i = 0; i < this.spanningTreeChildren.length; i++) {
        if (vertexId === void 0 || vertexId != this.spanningTreeChildren[i]) {
          neighbours.push(this.spanningTreeChildren[i]);
        }
      }
      if (this.parentVertexId != null) {
        if (vertexId === void 0 || vertexId != this.parentVertexId) {
          neighbours.push(this.parentVertexId);
        }
      }
      return neighbours;
    }
    /**
     * Gets the next vertex in the ring in opposide direction to the supplied vertex id.
     *
     * @param {Vertex[]} vertices The array of vertices for the current molecule.
     * @param {Number} ringId The id of the ring containing this vertex.
     * @param {Number} previousVertexId The id of the previous vertex. The next vertex will be opposite from the vertex with this id as seen from this vertex.
     * @returns {Number} The id of the next vertex in the ring.
     */
    getNextInRing(vertices, ringId, previousVertexId) {
      let neighbours = this.getNeighbours();
      for (let i = 0; i < neighbours.length; i++) {
        if (ArrayHelper.contains(vertices[neighbours[i]].value.rings, { value: ringId }) && neighbours[i] != previousVertexId) {
          return neighbours[i];
        }
      }
      return null;
    }
  };

  // node_modules/smiles-drawer/src/RingConnection.js
  var RingConnection = class {
    /**
     * The constructor for the class RingConnection.
     *
     * @param {Ring} firstRing A ring.
     * @param {Ring} secondRing A ring.
     */
    constructor(firstRing, secondRing) {
      this.id = null;
      this.firstRingId = firstRing.id;
      this.secondRingId = secondRing.id;
      this.vertices = /* @__PURE__ */ new Set();
      for (let m = 0; m < firstRing.members.length; m++) {
        let c = firstRing.members[m];
        for (let n = 0; n < secondRing.members.length; n++) {
          let d = secondRing.members[n];
          if (c === d) {
            this.addVertex(c);
          }
        }
      }
    }
    /**
     * Adding a vertex to the ring connection.
     *
     * @param {Number} vertexId A vertex id.
     */
    addVertex(vertexId) {
      this.vertices.add(vertexId);
    }
    /**
     * Update the ring id of this ring connection that is not the ring id supplied as the second argument.
     *
     * @param {Number} ringId A ring id. The new ring id to be set.
     * @param {Number} otherRingId A ring id. The id that is NOT to be updated.
     */
    updateOther(ringId, otherRingId) {
      if (this.firstRingId === otherRingId) {
        this.secondRingId = ringId;
      } else {
        this.firstRingId = ringId;
      }
    }
    /**
     * Returns a boolean indicating whether or not a ring with a given id is participating in this ring connection.
     *
     * @param {Number} ringId A ring id.
     * @returns {Boolean} A boolean indicating whether or not a ring with a given id participates in this ring connection.
     */
    containsRing(ringId) {
      return this.firstRingId === ringId || this.secondRingId === ringId;
    }
    /**
     * Checks whether or not this ring connection is a bridge in a bridged ring.
     *
     * @param {Vertex[]} vertices The array of vertices associated with the current molecule.
     * @returns {Boolean} A boolean indicating whether or not this ring connection is a bridge.
     */
    isBridge(vertices) {
      if (this.vertices.size > 2) {
        return true;
      }
      if (this.vertices.size === 2) {
        let [v1, v2] = [...this.vertices];
        let v2NeighbourSet = new Set(vertices[v2].neighbours);
        for (let n of vertices[v1].neighbours) {
          if (n !== v2 && v2NeighbourSet.has(n)) {
            let nRings = vertices[n].value.rings;
            if (nRings.includes(this.firstRingId) || nRings.includes(this.secondRingId)) {
              return true;
            }
          }
        }
      }
      return false;
    }
    /**
     * Checks whether or not two rings are connected by a bridged bond.
     *
     * @static
     * @param {RingConnection[]} ringConnections An array of ring connections containing the ring connections associated with the current molecule.
     * @param {Vertex[]} vertices An array of vertices containing the vertices associated with the current molecule.
     * @param {Number} firstRingId A ring id.
     * @param {Number} secondRingId A ring id.
     * @returns {Boolean} A boolean indicating whether or not two rings ar connected by a bridged bond.
     */
    static isBridge(ringConnections, vertices, firstRingId, secondRingId) {
      let ringConnection = null;
      for (let i = 0; i < ringConnections.length; i++) {
        ringConnection = ringConnections[i];
        if (ringConnection.firstRingId === firstRingId && ringConnection.secondRingId === secondRingId || ringConnection.firstRingId === secondRingId && ringConnection.secondRingId === firstRingId) {
          return ringConnection.isBridge(vertices);
        }
      }
      return false;
    }
    /**
     * Retruns the neighbouring rings of a given ring.
     *
     * @static
     * @param {RingConnection[]} ringConnections An array of ring connections containing ring connections associated with the current molecule.
     * @param {Number} ringId A ring id.
     * @returns {Number[]} An array of ring ids of neighbouring rings.
     */
    static getNeighbours(ringConnections, ringId) {
      let neighbours = [];
      for (let i = 0; i < ringConnections.length; i++) {
        let ringConnection = ringConnections[i];
        if (ringConnection.firstRingId === ringId) {
          neighbours.push(ringConnection.secondRingId);
        } else if (ringConnection.secondRingId === ringId) {
          neighbours.push(ringConnection.firstRingId);
        }
      }
      return neighbours;
    }
    /**
     * Returns an array of vertex ids associated with a given ring connection.
     *
     * @static
     * @param {RingConnection[]} ringConnections An array of ring connections containing ring connections associated with the current molecule.
     * @param {Number} firstRingId A ring id.
     * @param {Number} secondRingId A ring id.
     * @returns {Number[]} An array of vertex ids associated with the ring connection.
     */
    static getVertices(ringConnections, firstRingId, secondRingId) {
      for (let i = 0; i < ringConnections.length; i++) {
        let ringConnection = ringConnections[i];
        if (ringConnection.firstRingId === firstRingId && ringConnection.secondRingId === secondRingId || ringConnection.firstRingId === secondRingId && ringConnection.secondRingId === firstRingId) {
          return [...ringConnection.vertices];
        }
      }
    }
  };

  // node_modules/smiles-drawer/src/Ring.js
  var Ring = class _Ring {
    /**
     * The constructor for the class Ring.
     *
     * @param {Number[]} members An array containing the vertex ids of the members of the ring to be created.
     */
    constructor(members) {
      this.id = null;
      this.members = members;
      this.edges = [];
      this.insiders = [];
      this.neighbours = [];
      this.positioned = false;
      this.center = new Vector2(0, 0);
      this.rings = [];
      this.isBridged = false;
      this.isPartOfBridged = false;
      this.isSpiro = false;
      this.isFused = false;
      this.centralAngle = 0;
      this.canFlip = true;
    }
    /**
     * Clones this ring and returns the clone.
     *
     * @returns {Ring} A clone of this ring.
     */
    clone() {
      let clone = new _Ring(this.members);
      clone.id = this.id;
      clone.insiders = ArrayHelper.clone(this.insiders);
      clone.neighbours = ArrayHelper.clone(this.neighbours);
      clone.positioned = this.positioned;
      clone.center = this.center.clone();
      clone.rings = ArrayHelper.clone(this.rings);
      clone.isBridged = this.isBridged;
      clone.isPartOfBridged = this.isPartOfBridged;
      clone.isSpiro = this.isSpiro;
      clone.isFused = this.isFused;
      clone.centralAngle = this.centralAngle;
      clone.canFlip = this.canFlip;
      return clone;
    }
    /**
     * Returns the size (number of members) of this ring.
     *
     * @returns {Number} The size (number of members) of this ring.
     */
    getSize() {
      return this.members.length;
    }
    /**
     * Gets the polygon representation (an array of the ring-members positional vectors) of this ring.
     *
     * @param {Vertex[]} vertices An array of vertices representing the current molecule.
     * @returns {Vector2[]} An array of the positional vectors of the ring members.
     */
    getPolygon(vertices) {
      let polygon = [];
      for (let i = 0; i < this.members.length; i++) {
        polygon.push(vertices[this.members[i]].position);
      }
      return polygon;
    }
    /**
     * Returns the angle of this ring in relation to the coordinate system.
     *
     * @returns {Number} The angle in radians.
     */
    getAngle() {
      return Math.PI - this.centralAngle;
    }
    /**
     * Loops over the members of this ring from a given start position in a direction opposite to the vertex id passed as the previousId.
     *
     * @param {Vertex[]} vertices The vertices associated with the current molecule.
     * @param {Function} callback A callback with the current vertex id as a parameter.
     * @param {Number} startVertexId The vertex id of the start vertex.
     * @param {Number} previousVertexId The vertex id of the previous vertex (the loop calling the callback function will run in the opposite direction of this vertex).
     */
    eachMember(vertices, callback, startVertexId, previousVertexId) {
      startVertexId = startVertexId || startVertexId === 0 ? startVertexId : this.members[0];
      let current = startVertexId;
      let max5 = 0;
      while (current != null && max5 < 100) {
        let prev = current;
        callback(prev);
        current = vertices[current].getNextInRing(vertices, this.id, previousVertexId);
        previousVertexId = prev;
        if (current == startVertexId) {
          current = null;
        }
        max5++;
      }
    }
    /**
     * Returns an array containing the neighbouring rings of this ring ordered by ring size.
     *
     * @param {RingConnection[]} ringConnections An array of ring connections associated with the current molecule.
     * @returns {Object[]} An array of neighbouring rings sorted by ring size. Example: { n: 5, neighbour: 1 }.
     */
    getOrderedNeighbours(ringConnections) {
      let orderedNeighbours = Array(this.neighbours.length);
      for (let i = 0; i < this.neighbours.length; i++) {
        let vertices = RingConnection.getVertices(ringConnections, this.id, this.neighbours[i]);
        orderedNeighbours[i] = {
          n: vertices.length,
          neighbour: this.neighbours[i]
        };
      }
      orderedNeighbours.sort((a, b) => b.n - a.n);
      return orderedNeighbours;
    }
    /**
     * Check whether this ring is an implicitly defined benzene-like (e.g. C1=CC=CC=C1) with 6 members and 3 double bonds.
     *
     * @param {Vertex[]} vertices An array of vertices associated with the current molecule.
     * @returns {Boolean} A boolean indicating whether or not this ring is an implicitly defined benzene-like.
     */
    isBenzeneLike(vertices) {
      let db = this.getDoubleBondCount(vertices);
      let length = this.members.length;
      return db === 3 && length === 6 || db === 2 && length === 5;
    }
    /**
     * Get the number of double bonds inside this ring.
     *
     * @param {Vertex[]} vertices An array of vertices associated with the current molecule.
     * @returns {Number} The number of double bonds inside this ring.
     */
    getDoubleBondCount(vertices) {
      let doubleBondCount = 0;
      for (let i = 0; i < this.members.length; i++) {
        let atom = vertices[this.members[i]].value;
        if (atom.bondType === "=" || atom.branchBond === "=") {
          doubleBondCount++;
        }
      }
      return doubleBondCount;
    }
    /**
     * Checks whether or not this ring contains a member with a given vertex id.
     *
     * @param {Number} vertexId A vertex id.
     * @returns {Boolean} A boolean indicating whether or not this ring contains a member with the given vertex id.
     */
    contains(vertexId) {
      for (let i = 0; i < this.members.length; i++) {
        if (this.members[i] == vertexId) {
          return true;
        }
      }
      return false;
    }
  };

  // node_modules/smiles-drawer/src/ThemeManager.js
  var ThemeManager = class {
    constructor(colors, theme) {
      this.colors = colors;
      this.theme = this.colors[theme];
    }
    /**
     * Returns the hex code of a color associated with a key from the current theme.
     *
     * @param {String} key The color key in the theme (e.g. C, N, BACKGROUND, ...).
     * @returns {String} A color hex value.
     */
    getColor(key) {
      if (key) {
        key = key.toUpperCase();
        if (key in this.theme) {
          return this.theme[key];
        }
      }
      return this.theme["C"];
    }
    /**
     * Sets the theme to the specified string if it exists. If it does not, this
     * does nothing.
     *
     * @param {String} theme the name of the theme to switch to
     */
    setTheme(theme) {
      if (theme in this.colors) {
        this.theme = this.colors[theme];
      }
    }
  };

  // node_modules/smiles-drawer/src/CanvasWrapper.js
  function getChargeText(charge) {
    if (!charge) {
      return "";
    } else if (charge === 1) {
      return "+";
    } else if (charge === -1) {
      return "-";
    } else if (charge > 0) {
      return charge + "+";
    } else {
      return charge + "-";
    }
  }
  var CanvasWrapper = class {
    /**
     * The constructor for the class CanvasWrapper.
     *
     * @param {string|String|HTMLCanvasElement} target The canvas id or the HTMLCanvasElement.
     * @param {ThemeManager} themeManager Theme manager for setting proper colors.
     * @param {Object} options The smiles drawer options object.
     */
    constructor(target, themeManager, options) {
      let element = null;
      if (target instanceof String) {
        element = document.getElementById(target.valueOf());
      } else if (typeof target === "string") {
        element = document.getElementById(target);
      } else {
        element = target;
      }
      if (element instanceof HTMLCanvasElement) {
        this.canvas = element;
      } else {
        throw Error("First argument was not a canvas or the ID of a canvas.");
      }
      this.ctx = this.canvas.getContext("2d");
      this.themeManager = themeManager;
      this.opts = options;
      this.drawingWidth = 0;
      this.drawingHeight = 0;
      this.offsetX = 0;
      this.offsetY = 0;
      this.fontLarge = this.opts.fontSizeLarge + "pt Helvetica, Arial, sans-serif";
      this.fontSmall = this.opts.fontSizeSmall + "pt Helvetica, Arial, sans-serif";
      this.updateSize(this.opts.width, this.opts.height);
      this.ctx.font = this.fontLarge;
      this.hydrogenWidth = this.ctx.measureText("H").width;
      this.halfHydrogenWidth = this.hydrogenWidth / 2;
      this.halfBondThickness = this.opts.bondThickness / 2;
    }
    /**
     * Update the width and height of the canvas
     *
     * @param {Number} width
     * @param {Number} height
     */
    updateSize(width, height) {
      this.ratio = window.devicePixelRatio || 1;
      if (this.ratio !== 1) {
        this.canvas.width = width * this.ratio;
        this.canvas.height = height * this.ratio;
        this.canvas.style.width = width + "px";
        this.canvas.style.height = height + "px";
        this.ctx.setTransform(this.ratio, 0, 0, this.ratio, 0, 0);
      } else {
        this.canvas.width = width * this.ratio;
        this.canvas.height = height * this.ratio;
      }
    }
    /**
     * Sets a provided theme.
     *
     * @param {Object} theme A theme from the smiles drawer options.
     */
    setTheme(theme) {
      this.colors = theme;
    }
    /**
     * Scale the canvas based on vertex positions.
     *
     * @param {Vertex[]} vertices An array of vertices containing the vertices associated with the current molecule.
     */
    scale(vertices) {
      let maxX = -Number.MAX_VALUE;
      let maxY = -Number.MAX_VALUE;
      let minX = Number.MAX_VALUE;
      let minY = Number.MAX_VALUE;
      for (let i = 0; i < vertices.length; i++) {
        if (!vertices[i].value.isDrawn) {
          continue;
        }
        let p = vertices[i].position;
        if (maxX < p.x) maxX = p.x;
        if (maxY < p.y) maxY = p.y;
        if (minX > p.x) minX = p.x;
        if (minY > p.y) minY = p.y;
      }
      let padding = this.opts.padding;
      maxX += padding;
      maxY += padding;
      minX -= padding;
      minY -= padding;
      this.drawingWidth = maxX - minX;
      this.drawingHeight = maxY - minY;
      let scaleX = this.canvas.offsetWidth / this.drawingWidth;
      let scaleY = this.canvas.offsetHeight / this.drawingHeight;
      let scale = scaleX < scaleY ? scaleX : scaleY;
      this.ctx.scale(scale, scale);
      this.offsetX = -minX;
      this.offsetY = -minY;
      if (scaleX < scaleY) {
        this.offsetY += this.canvas.offsetHeight / (2 * scale) - this.drawingHeight / 2;
      } else {
        this.offsetX += this.canvas.offsetWidth / (2 * scale) - this.drawingWidth / 2;
      }
    }
    /**
     * Resets the transform of the canvas.
     */
    reset() {
      this.ctx.setTransform(1, 0, 0, 1, 0, 0);
    }
    /**
     * Returns the hex code of a color associated with a key from the current theme.
     *
     * @param {String} key The color key in the theme (e.g. C, N, BACKGROUND, ...).
     * @returns {String} A color hex value.
     */
    getColor(key) {
      key = key.toUpperCase();
      if (key in this.colors) {
        return this.colors[key];
      }
      return this.colors["C"];
    }
    /**
     * Draws a circle to a canvas context.
     * @param {Number} x The x coordinate of the circles center.
     * @param {Number} y The y coordinate of the circles center.
     * @param {Number} radius The radius of the circle
     * @param {String} color A hex encoded color.
     * @param {Boolean} [fill=true] Whether to fill or stroke the circle.
     * @param {Boolean} [debug=false] Draw in debug mode.
     * @param {String} [debugText=''] A debug message.
     */
    drawCircle(x, y, radius, color, fill = true, debug = false, debugText = "") {
      let ctx = this.ctx;
      let offsetX = this.offsetX;
      let offsetY = this.offsetY;
      ctx.save();
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(x + offsetX, y + offsetY, radius, 0, MathHelper.twoPI, true);
      ctx.closePath();
      if (debug) {
        if (fill) {
          ctx.fillStyle = "#f00";
          ctx.fill();
        } else {
          ctx.strokeStyle = "#f00";
          ctx.stroke();
        }
        this.drawDebugText(x, y, debugText);
      } else {
        if (fill) {
          ctx.fillStyle = color;
          ctx.fill();
        } else {
          ctx.strokeStyle = color;
          ctx.stroke();
        }
      }
      ctx.restore();
    }
    /**
     * Draw a line to a canvas.
     *
     * @param {Line} line A line.
     * @param {Boolean} [dashed=false] Whether or not the line is dashed.
     * @param {Number} [alpha=1.0] The alpha value of the color.
     */
    drawLine(line, dashed = false, alpha = 1) {
      let ctx = this.ctx;
      let offsetX = this.offsetX;
      let offsetY = this.offsetY;
      let shortLine = line.clone().shorten(4);
      let l = shortLine.getLeftVector().clone();
      let r = shortLine.getRightVector().clone();
      l.x += offsetX;
      l.y += offsetY;
      r.x += offsetX;
      r.y += offsetY;
      if (!dashed) {
        ctx.save();
        ctx.globalCompositeOperation = "destination-out";
        ctx.beginPath();
        ctx.moveTo(l.x, l.y);
        ctx.lineTo(r.x, r.y);
        ctx.lineCap = "round";
        ctx.lineWidth = this.opts.bondThickness + 1.2;
        ctx.strokeStyle = this.themeManager.getColor("BACKGROUND");
        ctx.stroke();
        ctx.globalCompositeOperation = "source-over";
        ctx.restore();
      }
      l = line.getLeftVector().clone();
      r = line.getRightVector().clone();
      l.x += offsetX;
      l.y += offsetY;
      r.x += offsetX;
      r.y += offsetY;
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(l.x, l.y);
      ctx.lineTo(r.x, r.y);
      ctx.lineCap = "round";
      ctx.lineWidth = this.opts.bondThickness;
      let gradient = this.ctx.createLinearGradient(l.x, l.y, r.x, r.y);
      gradient.addColorStop(0.4, this.themeManager.getColor(line.getLeftElement()) || this.themeManager.getColor("C"));
      gradient.addColorStop(0.6, this.themeManager.getColor(line.getRightElement()) || this.themeManager.getColor("C"));
      if (dashed) {
        ctx.setLineDash([1, 1.5]);
        ctx.lineWidth = this.opts.bondThickness / 1.5;
      }
      if (alpha < 1) {
        ctx.globalAlpha = alpha;
      }
      ctx.strokeStyle = gradient;
      ctx.stroke();
      ctx.restore();
    }
    /**
     * Draw a wedge on the canvas.
     *
     * @param {Line} line A line.
     * @param {Number} width The wedge width.
     */
    drawWedge(line, width = 1) {
      if (isNaN(line.from.x) || isNaN(line.from.y) || isNaN(line.to.x) || isNaN(line.to.y)) {
        return;
      }
      let ctx = this.ctx;
      let offsetX = this.offsetX;
      let offsetY = this.offsetY;
      let shortLine = line.clone().shorten(5);
      let l = shortLine.getLeftVector().clone();
      let r = shortLine.getRightVector().clone();
      l.x += offsetX;
      l.y += offsetY;
      r.x += offsetX;
      r.y += offsetY;
      l = line.getLeftVector().clone();
      r = line.getRightVector().clone();
      l.x += offsetX;
      l.y += offsetY;
      r.x += offsetX;
      r.y += offsetY;
      ctx.save();
      let normals = Vector2.normals(l, r);
      normals[0].normalize();
      normals[1].normalize();
      let isRightChiralCenter = line.getRightChiral();
      let start = l;
      let end = r;
      if (isRightChiralCenter) {
        start = r;
        end = l;
      }
      let t = Vector2.add(start, Vector2.multiplyScalar(normals[0], this.halfBondThickness));
      let u = Vector2.add(end, Vector2.multiplyScalar(normals[0], 1.5 + this.halfBondThickness));
      let v = Vector2.add(end, Vector2.multiplyScalar(normals[1], 1.5 + this.halfBondThickness));
      let w = Vector2.add(start, Vector2.multiplyScalar(normals[1], this.halfBondThickness));
      ctx.beginPath();
      ctx.moveTo(t.x, t.y);
      ctx.lineTo(u.x, u.y);
      ctx.lineTo(v.x, v.y);
      ctx.lineTo(w.x, w.y);
      let gradient = this.ctx.createRadialGradient(r.x, r.y, this.opts.bondLength, r.x, r.y, 0);
      gradient.addColorStop(0.4, this.themeManager.getColor(line.getLeftElement()) || this.themeManager.getColor("C"));
      gradient.addColorStop(0.6, this.themeManager.getColor(line.getRightElement()) || this.themeManager.getColor("C"));
      ctx.fillStyle = gradient;
      ctx.fill();
      ctx.restore();
    }
    /**
     * Draw a dashed wedge on the canvas.
     *
     * @param {Line} line A line.
     */
    drawDashedWedge(line) {
      if (isNaN(line.from.x) || isNaN(line.from.y) || isNaN(line.to.x) || isNaN(line.to.y)) {
        return;
      }
      let ctx = this.ctx;
      let offsetX = this.offsetX;
      let offsetY = this.offsetY;
      let l = line.getLeftVector().clone();
      let r = line.getRightVector().clone();
      l.x += offsetX;
      l.y += offsetY;
      r.x += offsetX;
      r.y += offsetY;
      ctx.save();
      let normals = Vector2.normals(l, r);
      normals[0].normalize();
      normals[1].normalize();
      let isRightChiralCenter = line.getRightChiral();
      let start;
      let end;
      let sStart;
      let sEnd;
      let shortLine = line.clone();
      if (isRightChiralCenter) {
        start = r;
        end = l;
        shortLine.shortenRight(1);
        sStart = shortLine.getRightVector().clone();
        sEnd = shortLine.getLeftVector().clone();
      } else {
        start = l;
        end = r;
        shortLine.shortenLeft(1);
        sStart = shortLine.getLeftVector().clone();
        sEnd = shortLine.getRightVector().clone();
      }
      sStart.x += offsetX;
      sStart.y += offsetY;
      sEnd.x += offsetX;
      sEnd.y += offsetY;
      let dir = Vector2.subtract(end, start).normalize();
      ctx.strokeStyle = this.themeManager.getColor("C");
      ctx.lineCap = "round";
      ctx.lineWidth = this.opts.bondThickness;
      ctx.beginPath();
      let length = line.getLength();
      let step = 1.25 / (length / (this.opts.bondThickness * 3));
      let changed = false;
      for (let t = 0; t < 1; t += step) {
        let to = Vector2.multiplyScalar(dir, t * length);
        let startDash = Vector2.add(start, to);
        let width = 1.5 * t;
        let dashOffset = Vector2.multiplyScalar(normals[0], width);
        if (!changed && t > 0.5) {
          ctx.stroke();
          ctx.beginPath();
          ctx.strokeStyle = this.themeManager.getColor(line.getRightElement()) || this.themeManager.getColor("C");
          changed = true;
        }
        startDash.subtract(dashOffset);
        ctx.moveTo(startDash.x, startDash.y);
        startDash.add(Vector2.multiplyScalar(dashOffset, 2));
        ctx.lineTo(startDash.x, startDash.y);
      }
      ctx.stroke();
      ctx.restore();
    }
    /**
     * Draws a debug text message at a given position
     *
     * @param {Number} x The x coordinate.
     * @param {Number} y The y coordinate.
     * @param {String} text The debug text.
     */
    drawDebugText(x, y, text) {
      let ctx = this.ctx;
      ctx.save();
      ctx.font = "5px Droid Sans, sans-serif";
      ctx.textAlign = "start";
      ctx.textBaseline = "top";
      ctx.fillStyle = "#ff0000";
      ctx.fillText(text, x + this.offsetX, y + this.offsetY);
      ctx.restore();
    }
    /**
     * Draw a ball to the canvas.
     *
     * @param {Number} x The x position of the text.
     * @param {Number} y The y position of the text.
     * @param {String} elementName The name of the element (single-letter).
     */
    drawBall(x, y, elementName) {
      let ctx = this.ctx;
      ctx.save();
      ctx.beginPath();
      ctx.arc(x + this.offsetX, y + this.offsetY, this.opts.bondLength / 4.5, 0, MathHelper.twoPI, false);
      ctx.fillStyle = this.themeManager.getColor(elementName);
      ctx.fill();
      ctx.restore();
    }
    /**
     * Draw a point to the canvas.
     *
     * @param {Number} x The x position of the point.
     * @param {Number} y The y position of the point.
     * @param {String} elementName The name of the element (single-letter).
     */
    drawPoint(x, y, elementName) {
      let ctx = this.ctx;
      let offsetX = this.offsetX;
      let offsetY = this.offsetY;
      ctx.save();
      ctx.globalCompositeOperation = "destination-out";
      ctx.beginPath();
      ctx.arc(x + offsetX, y + offsetY, 1.5, 0, MathHelper.twoPI, true);
      ctx.closePath();
      ctx.fill();
      ctx.globalCompositeOperation = "source-over";
      ctx.beginPath();
      ctx.arc(x + this.offsetX, y + this.offsetY, 0.75, 0, MathHelper.twoPI, false);
      ctx.fillStyle = this.themeManager.getColor(elementName);
      ctx.fill();
      ctx.restore();
    }
    /**
     * Draw a text to the canvas.
     *
     * @param {Number} x The x position of the text.
     * @param {Number} y The y position of the text.
     * @param {String} elementName The name of the element (single-letter).
     * @param {Number} hydrogens The number of hydrogen atoms.
     * @param {String} direction The direction of the text in relation to the associated vertex.
     * @param {Boolean} isTerminal A boolean indicating whether or not the vertex is terminal.
     * @param {Number} charge The charge of the atom.
     * @param {Number} isotope The isotope number.
     * @param {Number} vertexCount The number of vertices in the molecular graph.
     * @param {Object} attachedPseudoElement A map with containing information for pseudo elements or concatinated elements. The key is comprised of the element symbol and the hydrogen count.
     * @param {String} attachedPseudoElement.element The element symbol.
     * @param {Number} attachedPseudoElement.count The number of occurences that match the key.
     * @param {Number} attachedPseudoElement.hyrogenCount The number of hydrogens attached to each atom matching the key.
     */
    drawText(x, y, elementName, hydrogens, direction, isTerminal, charge, isotope, vertexCount, attachedPseudoElement = {}) {
      let ctx = this.ctx;
      let offsetX = this.offsetX;
      let offsetY = this.offsetY;
      ctx.save();
      ctx.textAlign = "start";
      ctx.textBaseline = "alphabetic";
      let pseudoElementHandled = false;
      let chargeText = "";
      let chargeWidth = 0;
      if (charge) {
        chargeText = getChargeText(charge);
        ctx.font = this.fontSmall;
        chargeWidth = ctx.measureText(chargeText).width;
      }
      let isotopeText = "0";
      let isotopeWidth = 0;
      if (isotope > 0) {
        isotopeText = isotope.toString();
        ctx.font = this.fontSmall;
        isotopeWidth = ctx.measureText(isotopeText).width;
      }
      if (charge === 1 && elementName === "N" && "0O" in attachedPseudoElement && "0O-1" in attachedPseudoElement) {
        attachedPseudoElement = { "0O": { element: "O", count: 2, hydrogenCount: 0, previousElement: "C", charge: "" } };
        charge = 0;
      }
      ctx.font = this.fontLarge;
      ctx.fillStyle = this.themeManager.getColor("BACKGROUND");
      let dim = ctx.measureText(elementName);
      let r = dim.width > this.opts.fontSizeLarge ? dim.width : this.opts.fontSizeLarge;
      r /= 1.5;
      ctx.globalCompositeOperation = "destination-out";
      ctx.beginPath();
      ctx.arc(x + offsetX, y + offsetY, r, 0, MathHelper.twoPI, true);
      ctx.closePath();
      ctx.fill();
      ctx.globalCompositeOperation = "source-over";
      let cursorPos = -dim.width / 2;
      let cursorPosLeft = -dim.width / 2;
      ctx.fillStyle = this.themeManager.getColor(elementName);
      ctx.fillText(elementName, x + offsetX + cursorPos, y + this.opts.halfFontSizeLarge + offsetY);
      cursorPos += dim.width;
      if (charge) {
        ctx.font = this.fontSmall;
        ctx.fillText(chargeText, x + offsetX + cursorPos, y - this.opts.fifthFontSizeSmall + offsetY);
        cursorPos += chargeWidth;
      }
      if (isotope > 0) {
        ctx.font = this.fontSmall;
        ctx.fillText(isotopeText, x + offsetX + cursorPosLeft - isotopeWidth, y - this.opts.fifthFontSizeSmall + offsetY);
        cursorPosLeft -= isotopeWidth;
      }
      ctx.font = this.fontLarge;
      let hydrogenWidth = 0;
      let hydrogenCountWidth = 0;
      if (hydrogens === 1) {
        let hx = x + offsetX;
        let hy = y + offsetY + this.opts.halfFontSizeLarge;
        hydrogenWidth = this.hydrogenWidth;
        cursorPosLeft -= hydrogenWidth;
        if (direction === "left") {
          hx += cursorPosLeft;
        } else if (direction === "right") {
          hx += cursorPos;
        } else if (direction === "up" && isTerminal) {
          hx += cursorPos;
        } else if (direction === "down" && isTerminal) {
          hx += cursorPos;
        } else if (direction === "up" && !isTerminal) {
          hy -= this.opts.fontSizeLarge + this.opts.quarterFontSizeLarge;
          hx -= this.halfHydrogenWidth;
        } else if (direction === "down" && !isTerminal) {
          hy += this.opts.fontSizeLarge + this.opts.quarterFontSizeLarge;
          hx -= this.halfHydrogenWidth;
        }
        ctx.fillText("H", hx, hy);
        cursorPos += hydrogenWidth;
      } else if (hydrogens > 1) {
        let hx = x + offsetX;
        let hy = y + offsetY + this.opts.halfFontSizeLarge;
        hydrogenWidth = this.hydrogenWidth;
        ctx.font = this.fontSmall;
        hydrogenCountWidth = ctx.measureText(hydrogens.toString()).width;
        cursorPosLeft -= hydrogenWidth + hydrogenCountWidth;
        if (direction === "left") {
          hx += cursorPosLeft;
        } else if (direction === "right") {
          hx += cursorPos;
        } else if (direction === "up" && isTerminal) {
          hx += cursorPos;
        } else if (direction === "down" && isTerminal) {
          hx += cursorPos;
        } else if (direction === "up" && !isTerminal) {
          hy -= this.opts.fontSizeLarge + this.opts.quarterFontSizeLarge;
          hx -= this.halfHydrogenWidth;
        } else if (direction === "down" && !isTerminal) {
          hy += this.opts.fontSizeLarge + this.opts.quarterFontSizeLarge;
          hx -= this.halfHydrogenWidth;
        }
        ctx.font = this.fontLarge;
        ctx.fillText("H", hx, hy);
        ctx.font = this.fontSmall;
        ctx.fillText(hydrogens.toString(), hx + this.halfHydrogenWidth + hydrogenCountWidth, hy + this.opts.fifthFontSizeSmall);
        cursorPos += hydrogenWidth + this.halfHydrogenWidth + hydrogenCountWidth;
      }
      if (pseudoElementHandled) {
        ctx.restore();
        return;
      }
      for (const key of Object.keys(attachedPseudoElement)) {
        let openParenthesisWidth = 0;
        let closeParenthesisWidth = 0;
        let element = attachedPseudoElement[key].element;
        let elementCount = attachedPseudoElement[key].count;
        let hydrogenCount = attachedPseudoElement[key].hydrogenCount;
        let elementCharge = attachedPseudoElement[key].charge;
        ctx.font = this.fontLarge;
        if (elementCount > 1 && hydrogenCount > 0) {
          openParenthesisWidth = ctx.measureText("(").width;
          closeParenthesisWidth = ctx.measureText(")").width;
        }
        let elementWidth = ctx.measureText(element).width;
        let elementCountWidth = 0;
        let elementChargeText = "";
        let elementChargeWidth = 0;
        hydrogenWidth = 0;
        if (hydrogenCount > 0) {
          hydrogenWidth = this.hydrogenWidth;
        }
        ctx.font = this.fontSmall;
        if (elementCount > 1) {
          elementCountWidth = ctx.measureText(elementCount).width;
        }
        if (elementCharge !== 0) {
          elementChargeText = getChargeText(elementCharge);
          elementChargeWidth = ctx.measureText(elementChargeText).width;
        }
        hydrogenCountWidth = 0;
        if (hydrogenCount > 1) {
          hydrogenCountWidth = ctx.measureText(hydrogenCount).width;
        }
        ctx.font = this.fontLarge;
        let hx = x + offsetX;
        let hy = y + offsetY + this.opts.halfFontSizeLarge;
        ctx.fillStyle = this.themeManager.getColor(element);
        if (elementCount > 0) {
          cursorPosLeft -= elementCountWidth;
        }
        if (elementCount > 1 && hydrogenCount > 0) {
          if (direction === "left") {
            cursorPosLeft -= closeParenthesisWidth;
            ctx.fillText(")", hx + cursorPosLeft, hy);
          } else {
            ctx.fillText("(", hx + cursorPos, hy);
            cursorPos += openParenthesisWidth;
          }
        }
        if (direction === "left") {
          cursorPosLeft -= elementWidth;
          ctx.fillText(element, hx + cursorPosLeft, hy);
        } else {
          ctx.fillText(element, hx + cursorPos, hy);
          cursorPos += elementWidth;
        }
        if (hydrogenCount > 0) {
          if (direction === "left") {
            cursorPosLeft -= hydrogenWidth + hydrogenCountWidth;
            ctx.fillText("H", hx + cursorPosLeft, hy);
            if (hydrogenCount > 1) {
              ctx.font = this.fontSmall;
              ctx.fillText(hydrogenCount, hx + cursorPosLeft + hydrogenWidth, hy + this.opts.fifthFontSizeSmall);
            }
          } else {
            ctx.fillText("H", hx + cursorPos, hy);
            cursorPos += hydrogenWidth;
            if (hydrogenCount > 1) {
              ctx.font = this.fontSmall;
              ctx.fillText(hydrogenCount, hx + cursorPos, hy + this.opts.fifthFontSizeSmall);
              cursorPos += hydrogenCountWidth;
            }
          }
        }
        ctx.font = this.fontLarge;
        if (elementCount > 1 && hydrogenCount > 0) {
          if (direction === "left") {
            cursorPosLeft -= openParenthesisWidth;
            ctx.fillText("(", hx + cursorPosLeft, hy);
          } else {
            ctx.fillText(")", hx + cursorPos, hy);
            cursorPos += closeParenthesisWidth;
          }
        }
        ctx.font = this.fontSmall;
        if (elementCount > 1) {
          if (direction === "left") {
            ctx.fillText(elementCount, hx + cursorPosLeft + openParenthesisWidth + closeParenthesisWidth + hydrogenWidth + hydrogenCountWidth + elementWidth, hy + this.opts.fifthFontSizeSmall);
          } else {
            ctx.fillText(elementCount, hx + cursorPos, hy + this.opts.fifthFontSizeSmall);
            cursorPos += elementCountWidth;
          }
        }
        if (elementCharge !== 0) {
          if (direction === "left") {
            ctx.fillText(elementChargeText, hx + cursorPosLeft + openParenthesisWidth + closeParenthesisWidth + hydrogenWidth + hydrogenCountWidth + elementWidth, y - this.opts.fifthFontSizeSmall + offsetY);
          } else {
            ctx.fillText(elementChargeText, hx + cursorPos, y - this.opts.fifthFontSizeSmall + offsetY);
            cursorPos += elementChargeWidth;
          }
        }
      }
      ctx.restore();
    }
    /**
     * Draws a dubug dot at a given coordinate and adds text.
     *
     * @param {Number} x The x coordinate.
     * @param {Number} y The y coordindate.
     * @param {String} [debugText=''] A string.
     * @param {String} [color='#f00'] A color in hex form.
     */
    drawDebugPoint(x, y, debugText = "", color = "#f00") {
      this.drawCircle(x, y, 2, color, true, true, debugText);
    }
    /**
     * Draws a ring inside a provided ring, indicating aromaticity.
     *
     * @param {Ring} ring A ring.
     */
    drawAromaticityRing(ring) {
      let ctx = this.ctx;
      let radius = MathHelper.apothemFromSideLength(this.opts.bondLength, ring.getSize());
      ctx.save();
      ctx.strokeStyle = this.themeManager.getColor("C");
      ctx.lineWidth = this.opts.bondThickness;
      ctx.beginPath();
      ctx.arc(
        ring.center.x + this.offsetX,
        ring.center.y + this.offsetY,
        radius - this.opts.bondSpacing,
        0,
        Math.PI * 2,
        true
      );
      ctx.closePath();
      ctx.stroke();
      ctx.restore();
    }
    /**
     * Clear the canvas.
     *
     */
    clear() {
      this.ctx.clearRect(0, 0, this.canvas.offsetWidth, this.canvas.offsetHeight);
    }
  };

  // node_modules/smiles-drawer/src/Edge.js
  var Edge = class _Edge {
    /**
     * The constructor for the class Edge.
     *
     * @param {Number} sourceId A vertex id.
     * @param {Number} targetId A vertex id.
     * @param {Number} [weight=1] The weight of the edge.
     */
    constructor(sourceId, targetId, weight = 1) {
      this.id = null;
      this.sourceId = sourceId;
      this.targetId = targetId;
      this.weight = weight;
      this.bondType = "-";
      this.isPartOfAromaticRing = false;
      this.center = false;
      this.wedge = "";
    }
    /**
     * Set the bond type of this edge. This also sets the edge weight.
     * @param {String} bondType
     */
    setBondType(bondType) {
      this.bondType = bondType;
      this.weight = _Edge.bonds[bondType];
    }
    /**
     * An object mapping the bond type to the number of bonds.
     *
     * @returns {Object} The object containing the map.
     */
    static get bonds() {
      return {
        ".": 0,
        "-": 1,
        "/": 1,
        "\\": 1,
        "=": 2,
        "#": 3,
        "$": 4
      };
    }
  };

  // node_modules/smiles-drawer/src/Graph.js
  var Graph = class _Graph {
    /**
     * The constructor of the class Graph.
     *
     * @param {Object} parseTree A SMILES parse tree.
     * @param {Boolean} [isomeric=false] A boolean specifying whether or not the SMILES is isomeric.
     */
    constructor(parseTree, isomeric = false) {
      this.vertices = [];
      this.edges = [];
      this.atomIdxToVertexId = [];
      this.vertexIdsToEdgeId = {};
      this.isomeric = isomeric;
      this._atomIdx = 0;
      this._time = 0;
      this._init(parseTree);
    }
    /**
     * PRIVATE FUNCTION. Initializing the graph from the parse tree.
     *
     * @param {Object} node The current node in the parse tree.
     * @param {?Number} parentVertexId=null The id of the previous vertex.
     * @param {Boolean} isBranch=false Whether or not the bond leading to this vertex is a branch bond. Branches are represented by parentheses in smiles (e.g. CC(O)C).
     */
    _init(node, order = 0, parentVertexId = null, isBranch = false) {
      const element = node.atom.element ? node.atom.element : node.atom;
      let atom = new Atom(element, node.bond);
      if (element !== "H" || !node.hasNext && parentVertexId === null) {
        atom.idx = this._atomIdx;
        this._atomIdx++;
      }
      atom.branchBond = node.branchBond;
      atom.ringbonds = node.ringbonds;
      atom.bracket = node.atom.element ? node.atom : null;
      atom.class = node.atom.class;
      let vertex = new Vertex(atom);
      let parentVertex = this.vertices[parentVertexId];
      this.addVertex(vertex);
      if (atom.idx !== null) {
        this.atomIdxToVertexId.push(vertex.id);
      }
      if (parentVertexId !== null) {
        vertex.setParentVertexId(parentVertexId);
        vertex.value.addNeighbouringElement(parentVertex.value.element);
        parentVertex.addChild(vertex.id);
        parentVertex.value.addNeighbouringElement(atom.element);
        parentVertex.spanningTreeChildren.push(vertex.id);
        let edge = new Edge(parentVertexId, vertex.id, 1);
        if (isBranch) {
          edge.setBondType(vertex.value.branchBond || "-");
        } else {
          edge.setBondType(parentVertex.value.bondType || "-");
        }
        this.addEdge(edge);
      }
      let offset = node.ringbondCount + 1;
      if (atom.bracket) {
        offset += atom.bracket.hcount;
      }
      let stereoHydrogens = 0;
      if (atom.bracket && atom.bracket.chirality) {
        atom.isStereoCenter = true;
        stereoHydrogens = atom.bracket.hcount;
        for (let i = 0; i < stereoHydrogens; i++) {
          this._init({
            atom: "H",
            isBracket: "false",
            branches: [],
            branchCount: 0,
            ringbonds: [],
            ringbondCount: false,
            next: null,
            hasNext: false,
            bond: "-"
          }, i, vertex.id, true);
        }
      }
      for (let i = 0; i < node.branchCount; i++) {
        this._init(node.branches[i], i + offset, vertex.id, true);
      }
      if (node.hasNext) {
        this._init(node.next, node.branchCount + offset, vertex.id);
      }
    }
    /**
     * Clears all the elements in this graph (edges and vertices).
     */
    clear() {
      this.vertices = [];
      this.edges = [];
      this.vertexIdsToEdgeId = {};
    }
    /**
     * Add a vertex to the graph.
     *
     * @param {Vertex} vertex A new vertex.
     * @returns {Number} The vertex id of the new vertex.
     */
    addVertex(vertex) {
      vertex.id = this.vertices.length;
      this.vertices.push(vertex);
      return vertex.id;
    }
    /**
     * Add an edge to the graph.
     *
     * @param {Edge} edge A new edge.
     * @returns {Number} The edge id of the new edge.
     */
    addEdge(edge) {
      let source = this.vertices[edge.sourceId];
      let target = this.vertices[edge.targetId];
      edge.id = this.edges.length;
      this.edges.push(edge);
      this.vertexIdsToEdgeId[edge.sourceId + "_" + edge.targetId] = edge.id;
      this.vertexIdsToEdgeId[edge.targetId + "_" + edge.sourceId] = edge.id;
      edge.isPartOfAromaticRing = source.value.isPartOfAromaticRing && target.value.isPartOfAromaticRing;
      source.value.bondCount += edge.weight;
      target.value.bondCount += edge.weight;
      source.edges.push(edge.id);
      target.edges.push(edge.id);
      return edge.id;
    }
    /**
     * Returns the edge between two given vertices.
     *
     * @param {Number} vertexIdA A vertex id.
     * @param {Number} vertexIdB A vertex id.
     * @returns {(Edge|null)} The edge or, if no edge can be found, null.
     */
    getEdge(vertexIdA, vertexIdB) {
      let edgeId = this.vertexIdsToEdgeId[vertexIdA + "_" + vertexIdB];
      return edgeId === void 0 ? null : this.edges[edgeId];
    }
    /**
     * Returns the ids of edges connected to a vertex.
     *
     * @param {Number} vertexId A vertex id.
     * @returns {Number[]} An array containing the ids of edges connected to the vertex.
     */
    getEdges(vertexId) {
      let edgeIds = [];
      let vertex = this.vertices[vertexId];
      for (let i = 0; i < vertex.neighbours.length; i++) {
        edgeIds.push(this.vertexIdsToEdgeId[vertexId + "_" + vertex.neighbours[i]]);
      }
      return edgeIds;
    }
    /**
     * Check whether or not two vertices are connected by an edge.
     *
     * @param {Number} vertexIdA A vertex id.
     * @param {Number} vertexIdB A vertex id.
     * @returns {Boolean} A boolean indicating whether or not two vertices are connected by an edge.
     */
    hasEdge(vertexIdA, vertexIdB) {
      return this.vertexIdsToEdgeId[vertexIdA + "_" + vertexIdB] !== void 0;
    }
    /**
     * Returns an array containing the vertex ids of this graph.
     *
     * @returns {Number[]} An array containing all vertex ids of this graph.
     */
    getVertexList() {
      let arr = [this.vertices.length];
      for (let i = 0; i < this.vertices.length; i++) {
        arr[i] = this.vertices[i].id;
      }
      return arr;
    }
    /**
     * Returns an array containing source, target arrays of this graphs edges.
     *
     * @returns {Array[]} An array containing source, target arrays of this graphs edges. Example: [ [ 2, 5 ], [ 6, 9 ] ].
     */
    getEdgeList() {
      let arr = Array(this.edges.length);
      for (let i = 0; i < this.edges.length; i++) {
        arr[i] = [this.edges[i].sourceId, this.edges[i].targetId];
      }
      return arr;
    }
    /**
     * Get the adjacency matrix of the graph.
     *
     * @returns {Array[]} The adjancency matrix of the molecular graph.
     */
    getAdjacencyMatrix() {
      let length = this.vertices.length;
      let adjacencyMatrix = Array(length);
      for (let i = 0; i < length; i++) {
        adjacencyMatrix[i] = new Array(length);
        adjacencyMatrix[i].fill(0);
      }
      for (let i = 0; i < this.edges.length; i++) {
        let edge = this.edges[i];
        adjacencyMatrix[edge.sourceId][edge.targetId] = 1;
        adjacencyMatrix[edge.targetId][edge.sourceId] = 1;
      }
      return adjacencyMatrix;
    }
    /**
     * Get the adjacency matrix of the graph with all bridges removed (thus the components). Thus the remaining vertices are all part of ring systems.
     *
     * @returns {Array[]} The adjancency matrix of the molecular graph with all bridges removed.
     */
    getComponentsAdjacencyMatrix() {
      let length = this.vertices.length;
      let adjacencyMatrix = Array(length);
      let bridges = this.getBridges();
      for (let i = 0; i < length; i++) {
        adjacencyMatrix[i] = new Array(length);
        adjacencyMatrix[i].fill(0);
      }
      for (let i = 0; i < this.edges.length; i++) {
        let edge = this.edges[i];
        adjacencyMatrix[edge.sourceId][edge.targetId] = 1;
        adjacencyMatrix[edge.targetId][edge.sourceId] = 1;
      }
      for (let i = 0; i < bridges.length; i++) {
        adjacencyMatrix[bridges[i][0]][bridges[i][1]] = 0;
        adjacencyMatrix[bridges[i][1]][bridges[i][0]] = 0;
      }
      return adjacencyMatrix;
    }
    /**
     * Get the adjacency matrix of a subgraph.
     *
     * @param {Number[]} vertexIds An array containing the vertex ids contained within the subgraph.
     * @returns {Array[]} The adjancency matrix of the subgraph.
     */
    getSubgraphAdjacencyMatrix(vertexIds) {
      let length = vertexIds.length;
      let adjacencyMatrix = Array(length);
      for (let i = 0; i < length; i++) {
        adjacencyMatrix[i] = new Array(length);
        adjacencyMatrix[i].fill(0);
        for (let j = 0; j < length; j++) {
          if (i === j) {
            continue;
          }
          if (this.hasEdge(vertexIds[i], vertexIds[j])) {
            adjacencyMatrix[i][j] = 1;
          }
        }
      }
      return adjacencyMatrix;
    }
    /**
     * Get the distance matrix of the graph.
     *
     * @returns {Array[]} The distance matrix of the graph.
     */
    getDistanceMatrix() {
      let length = this.vertices.length;
      let adja = this.getAdjacencyMatrix();
      let dist = Array(length);
      for (let i = 0; i < length; i++) {
        dist[i] = Array(length);
        dist[i].fill(Infinity);
      }
      for (let i = 0; i < length; i++) {
        for (let j = 0; j < length; j++) {
          if (adja[i][j] === 1) {
            dist[i][j] = 1;
          }
        }
      }
      for (let k = 0; k < length; k++) {
        for (let i = 0; i < length; i++) {
          for (let j = 0; j < length; j++) {
            if (dist[i][j] > dist[i][k] + dist[k][j]) {
              dist[i][j] = dist[i][k] + dist[k][j];
            }
          }
        }
      }
      return dist;
    }
    /**
     * Get the distance matrix of a subgraph.
     *
     * @param {Number[]} vertexIds An array containing the vertex ids contained within the subgraph.
     * @returns {Array[]} The distance matrix of the subgraph.
     */
    getSubgraphDistanceMatrix(vertexIds) {
      let length = vertexIds.length;
      let adja = this.getSubgraphAdjacencyMatrix(vertexIds);
      let dist = Array(length);
      for (let i = 0; i < length; i++) {
        dist[i] = Array(length);
        dist[i].fill(Infinity);
        dist[i][i] = 0;
      }
      for (let i = 0; i < length; i++) {
        for (let j = 0; j < length; j++) {
          if (adja[i][j] === 1) {
            dist[i][j] = 1;
          }
        }
      }
      for (let k = 0; k < length; k++) {
        for (let i = 0; i < length; i++) {
          for (let j = 0; j < length; j++) {
            if (dist[i][j] > dist[i][k] + dist[k][j]) {
              dist[i][j] = dist[i][k] + dist[k][j];
            }
          }
        }
      }
      return dist;
    }
    /**
     * Get the adjacency list of the graph.
     *
     * @returns {Array[]} The adjancency list of the graph.
     */
    getAdjacencyList() {
      let length = this.vertices.length;
      let adjacencyList = Array(length);
      for (let i = 0; i < length; i++) {
        adjacencyList[i] = [];
        for (let j = 0; j < length; j++) {
          if (i === j) {
            continue;
          }
          if (this.hasEdge(this.vertices[i].id, this.vertices[j].id)) {
            adjacencyList[i].push(j);
          }
        }
      }
      return adjacencyList;
    }
    /**
     * Get the adjacency list of a subgraph.
     *
     * @param {Number[]} vertexIds An array containing the vertex ids contained within the subgraph.
     * @returns {Array[]} The adjancency list of the subgraph.
     */
    getSubgraphAdjacencyList(vertexIds) {
      let length = vertexIds.length;
      let adjacencyList = Array(length);
      for (let i = 0; i < length; i++) {
        adjacencyList[i] = [];
        for (let j = 0; j < length; j++) {
          if (i === j) {
            continue;
          }
          if (this.hasEdge(vertexIds[i], vertexIds[j])) {
            adjacencyList[i].push(j);
          }
        }
      }
      return adjacencyList;
    }
    /**
     * Returns an array containing the edge ids of bridges. A bridge splits the graph into multiple components when removed.
     *
     * @returns {Number[]} An array containing the edge ids of the bridges.
     */
    getBridges() {
      let length = this.vertices.length;
      let visited = new Array(length);
      let disc = new Array(length);
      let low = new Array(length);
      let parent = new Array(length);
      let adj = this.getAdjacencyList();
      let outBridges = [];
      visited.fill(false);
      parent.fill(null);
      this._time = 0;
      for (let i = 0; i < length; i++) {
        if (!visited[i]) {
          this._bridgeDfs(i, visited, disc, low, parent, adj, outBridges);
        }
      }
      return outBridges;
    }
    /**
     * Traverses the graph in breadth-first order.
     *
     * @param {Number} startVertexId The id of the starting vertex.
     * @param {Function} callback The callback function to be called on every vertex.
     */
    traverseBF(startVertexId, callback) {
      let length = this.vertices.length;
      let visited = new Array(length);
      visited.fill(false);
      let queue = [startVertexId];
      while (queue.length > 0) {
        let u = queue.shift();
        let vertex = this.vertices[u];
        callback(vertex);
        for (let i = 0; i < vertex.neighbours.length; i++) {
          let v = vertex.neighbours[i];
          if (!visited[v]) {
            visited[v] = true;
            queue.push(v);
          }
        }
      }
    }
    /**
     * Get the depth of a subtree in the direction opposite to the vertex specified as the parent vertex.
     *
     * @param {Number} vertexId A vertex id.
     * @param {Number} parentVertexId The id of a neighbouring vertex.
     * @returns {Number} The depth of the sub-tree.
     */
    getTreeDepth(vertexId, parentVertexId) {
      if (vertexId === null || parentVertexId === null) {
        return 0;
      }
      let neighbours = this.vertices[vertexId].getSpanningTreeNeighbours(parentVertexId);
      let max5 = 0;
      for (let i = 0; i < neighbours.length; i++) {
        let childId = neighbours[i];
        let d = this.getTreeDepth(childId, vertexId);
        if (d > max5) {
          max5 = d;
        }
      }
      return max5 + 1;
    }
    /**
     * Traverse a sub-tree in the graph.
     *
     * @param {Number} vertexId A vertex id.
     * @param {Number} parentVertexId A neighbouring vertex.
     * @param {Function} callback The callback function that is called with each visited as an argument.
     * @param {Number} [maxDepth=999999] The maximum depth of the recursion.
     * @param {Boolean} [ignoreFirst=false] Whether or not to ignore the starting vertex supplied as vertexId in the callback.
     * @param {Number} [depth=1] The current depth in the tree.
     * @param {Uint8Array} [visited=null] An array holding a flag on whether or not a node has been visited.
     */
    traverseTree(vertexId, parentVertexId, callback, maxDepth = 999999, ignoreFirst = false, depth = 1, visited = null) {
      if (visited === null) {
        visited = new Uint8Array(this.vertices.length);
      }
      if (depth > maxDepth + 1 || visited[vertexId] === 1) {
        return;
      }
      visited[vertexId] = 1;
      let vertex = this.vertices[vertexId];
      let neighbours = vertex.getNeighbours(parentVertexId);
      if (!ignoreFirst || depth > 1) {
        callback(vertex);
      }
      for (let i = 0; i < neighbours.length; i++) {
        this.traverseTree(neighbours[i], vertexId, callback, maxDepth, ignoreFirst, depth + 1, visited);
      }
    }
    /**
     * Positiones the (sub)graph using Kamada and Kawais algorithm for drawing general undirected graphs. https://pdfs.semanticscholar.org/b8d3/bca50ccc573c5cb99f7d201e8acce6618f04.pdf
     * There are undocumented layout parameters. They are undocumented for a reason, so be very careful.
     *
     * @param {Number[]} vertexIds An array containing vertexIds to be placed using the force based layout.
     * @param {Vector2} center The center of the layout.
     * @param {Number} startVertexId A vertex id. Should be the starting vertex - e.g. the first to be positioned and connected to a previously place vertex.
     * @param {Ring} ring The bridged ring associated with this force-based layout.
     */
    kkLayout(vertexIds, center, startVertexId, ring, bondLength, threshold = 0.1, innerThreshold = 0.1, maxIteration = 2e3, maxInnerIteration = 50, maxEnergy = 1e9) {
      let edgeStrength = bondLength;
      let matDist = this.getSubgraphDistanceMatrix(vertexIds);
      let length = vertexIds.length;
      let radius = MathHelper.polyCircumradius(bondLength, length);
      let angle = MathHelper.centralAngle(length);
      let a = 0;
      let arrPositionX = new Float32Array(length);
      let arrPositionY = new Float32Array(length);
      let arrPositioned = Array(length);
      var i = length;
      while (i--) {
        let vertex = this.vertices[vertexIds[i]];
        if (!vertex.positioned) {
          arrPositionX[i] = center.x + Math.cos(a) * radius;
          arrPositionY[i] = center.y + Math.sin(a) * radius;
        } else {
          arrPositionX[i] = vertex.position.x;
          arrPositionY[i] = vertex.position.y;
        }
        arrPositioned[i] = vertex.positioned;
        a += angle;
      }
      let matLength = Array(length);
      i = length;
      while (i--) {
        matLength[i] = new Array(length);
        let j = length;
        while (j--) {
          matLength[i][j] = bondLength * matDist[i][j];
        }
      }
      let matStrength = Array(length);
      i = length;
      while (i--) {
        matStrength[i] = Array(length);
        let j = length;
        while (j--) {
          matStrength[i][j] = edgeStrength * Math.pow(matDist[i][j], -2);
        }
      }
      let matEnergy = Array(length);
      let arrEnergySumX = new Float32Array(length);
      let arrEnergySumY = new Float32Array(length);
      i = length;
      while (i--) {
        matEnergy[i] = Array(length);
      }
      i = length;
      while (i--) {
        let ux = arrPositionX[i];
        let uy = arrPositionY[i];
        let dEx = 0;
        let dEy = 0;
        let j = length;
        while (j--) {
          if (i === j) {
            continue;
          }
          let vx = arrPositionX[j];
          let vy = arrPositionY[j];
          let denom = 1 / Math.sqrt((ux - vx) * (ux - vx) + (uy - vy) * (uy - vy));
          matEnergy[i][j] = [
            matStrength[i][j] * (ux - vx - matLength[i][j] * (ux - vx) * denom),
            matStrength[i][j] * (uy - vy - matLength[i][j] * (uy - vy) * denom)
          ];
          matEnergy[j][i] = matEnergy[i][j];
          dEx += matEnergy[i][j][0];
          dEy += matEnergy[i][j][1];
        }
        arrEnergySumX[i] = dEx;
        arrEnergySumY[i] = dEy;
      }
      let energy = function(index) {
        return [arrEnergySumX[index] * arrEnergySumX[index] + arrEnergySumY[index] * arrEnergySumY[index], arrEnergySumX[index], arrEnergySumY[index]];
      };
      let highestEnergy = function() {
        let highEnergy = 0;
        let highEnergyId = 0;
        let highDEX = 0;
        let highDEY = 0;
        i = length;
        while (i--) {
          let [delta2, dEX2, dEY2] = energy(i);
          if (delta2 > highEnergy && arrPositioned[i] === false) {
            highEnergy = delta2;
            highEnergyId = i;
            highDEX = dEX2;
            highDEY = dEY2;
          }
        }
        return [highEnergyId, highEnergy, highDEX, highDEY];
      };
      let update = function(index, dEX2, dEY2) {
        let dxx = 0;
        let dyy = 0;
        let dxy = 0;
        let ux = arrPositionX[index];
        let uy = arrPositionY[index];
        let arrL = matLength[index];
        let arrK = matStrength[index];
        i = length;
        while (i--) {
          if (i === index) {
            continue;
          }
          let vx = arrPositionX[i];
          let vy = arrPositionY[i];
          let l = arrL[i];
          let k = arrK[i];
          let m = (ux - vx) * (ux - vx);
          let denom2 = 1 / Math.pow(m + (uy - vy) * (uy - vy), 1.5);
          dxx += k * (1 - l * (uy - vy) * (uy - vy) * denom2);
          dyy += k * (1 - l * m * denom2);
          dxy += k * (l * (ux - vx) * (uy - vy) * denom2);
        }
        if (dxx === 0) {
          dxx = 0.1;
        }
        if (dyy === 0) {
          dyy = 0.1;
        }
        if (dxy === 0) {
          dxy = 0.1;
        }
        let denom = dxy / dxx - dyy / dxy;
        let dy, dx;
        if (Math.abs(denom) < 1e-6) {
          dx = -dEX2 * 0.1;
          dy = -dEY2 * 0.1;
        } else {
          dy = (dEX2 / dxx + dEY2 / dxy) / denom;
          dx = -(dxy * dy + dEX2) / dxx;
        }
        let stepLen = Math.sqrt(dx * dx + dy * dy);
        if (stepLen > bondLength) {
          let scale = bondLength / stepLen;
          dx *= scale;
          dy *= scale;
        }
        arrPositionX[index] += dx;
        arrPositionY[index] += dy;
        let arrE = matEnergy[index];
        dEX2 = 0;
        dEY2 = 0;
        ux = arrPositionX[index];
        uy = arrPositionY[index];
        i = length;
        while (i--) {
          if (index === i) {
            continue;
          }
          let vx = arrPositionX[i];
          let vy = arrPositionY[i];
          let prevEx = arrE[i][0];
          let prevEy = arrE[i][1];
          let denom2 = 1 / Math.sqrt((ux - vx) * (ux - vx) + (uy - vy) * (uy - vy));
          dx = arrK[i] * (ux - vx - arrL[i] * (ux - vx) * denom2);
          dy = arrK[i] * (uy - vy - arrL[i] * (uy - vy) * denom2);
          arrE[i] = [dx, dy];
          dEX2 += dx;
          dEY2 += dy;
          arrEnergySumX[i] += dx - prevEx;
          arrEnergySumY[i] += dy - prevEy;
        }
        arrEnergySumX[index] = dEX2;
        arrEnergySumY[index] = dEY2;
      };
      let maxEnergyId = 0;
      let dEX = 0;
      let dEY = 0;
      let delta = 0;
      let iteration = 0;
      let innerIteration = 0;
      while (maxEnergy > threshold && maxIteration > iteration) {
        iteration++;
        [maxEnergyId, maxEnergy, dEX, dEY] = highestEnergy();
        delta = maxEnergy;
        innerIteration = 0;
        while (delta > innerThreshold && maxInnerIteration > innerIteration) {
          innerIteration++;
          update(maxEnergyId, dEX, dEY);
          [delta, dEX, dEY] = energy(maxEnergyId);
        }
      }
      i = length;
      while (i--) {
        let index = vertexIds[i];
        let vertex = this.vertices[index];
        vertex.position.x = arrPositionX[i];
        vertex.position.y = arrPositionY[i];
        vertex.positioned = true;
        vertex.forcePositioned = true;
      }
    }
    /**
     * PRIVATE FUNCTION used by getBridges().
     */
    _bridgeDfs(u, visited, disc, low, parent, adj, outBridges) {
      visited[u] = true;
      disc[u] = low[u] = ++this._time;
      for (let i = 0; i < adj[u].length; i++) {
        let v = adj[u][i];
        if (!visited[v]) {
          parent[v] = u;
          this._bridgeDfs(v, visited, disc, low, parent, adj, outBridges);
          low[u] = Math.min(low[u], low[v]);
          if (low[v] > disc[u]) {
            outBridges.push([u, v]);
          }
        } else if (v !== parent[u]) {
          low[u] = Math.min(low[u], disc[v]);
        }
      }
    }
    /**
     * Returns the connected components of the graph.
     *
     * @param {Array[]} adjacencyMatrix An adjacency matrix.
     * @returns {Set[]} Connected components as sets.
     */
    static getConnectedComponents(adjacencyMatrix) {
      let length = adjacencyMatrix.length;
      let visited = new Array(length);
      let components = [];
      visited.fill(false);
      for (let u = 0; u < length; u++) {
        if (!visited[u]) {
          let component = [];
          visited[u] = true;
          component.push(u);
          _Graph._ccGetDfs(u, visited, adjacencyMatrix, component);
          if (component.length > 1) {
            components.push(component);
          }
        }
      }
      return components;
    }
    /**
     * Returns the number of connected components for the graph.
     *
     * @param {Array[]} adjacencyMatrix An adjacency matrix.
     * @returns {Number} The number of connected components of the supplied graph.
     */
    static getConnectedComponentCount(adjacencyMatrix) {
      let length = adjacencyMatrix.length;
      let visited = new Array(length);
      let count = 0;
      visited.fill(false);
      for (let u = 0; u < length; u++) {
        if (!visited[u]) {
          visited[u] = true;
          count++;
          _Graph._ccCountDfs(u, visited, adjacencyMatrix);
        }
      }
      return count;
    }
    /**
     * PRIVATE FUNCTION used by getConnectedComponentCount().
     */
    static _ccCountDfs(u, visited, adjacencyMatrix) {
      for (let v = 0; v < adjacencyMatrix[u].length; v++) {
        let c = adjacencyMatrix[u][v];
        if (!c || visited[v] || u === v) {
          continue;
        }
        visited[v] = true;
        _Graph._ccCountDfs(v, visited, adjacencyMatrix);
      }
    }
    /**
     * PRIVATE FUNCTION used by getConnectedComponents().
     */
    static _ccGetDfs(u, visited, adjacencyMatrix, component) {
      for (let v = 0; v < adjacencyMatrix[u].length; v++) {
        let c = adjacencyMatrix[u][v];
        if (!c || visited[v] || u === v) {
          continue;
        }
        visited[v] = true;
        component.push(v);
        _Graph._ccGetDfs(v, visited, adjacencyMatrix, component);
      }
    }
  };

  // node_modules/smiles-drawer/src/Options.js
  var Options = class _Options {
    /**
     * A helper method to extend the default options with user supplied ones.
     */
    static extend() {
      let extended = {};
      let deep = false;
      let i = 0;
      let length = arguments.length;
      if (Object.prototype.toString.call(arguments[0]) === "[object Boolean]") {
        deep = arguments[0];
        i++;
      }
      let merge = function(obj) {
        for (let prop in obj) {
          if (Object.prototype.hasOwnProperty.call(obj, prop)) {
            if (deep && Object.prototype.toString.call(obj[prop]) === "[object Object]") {
              extended[prop] = _Options.extend(true, extended[prop], obj[prop]);
            } else {
              extended[prop] = obj[prop];
            }
          }
        }
      };
      for (; i < length; i++) {
        let obj = arguments[i];
        merge(obj);
      }
      return extended;
    }
  };

  // node_modules/smiles-drawer/src/SSSR.js
  var SSSR = class _SSSR {
    /**
     * Returns an array containing arrays, each representing a ring from the smallest set of smallest rings in the graph.
     *
     * @param {Graph} graph A Graph object.
     * @param {Boolean} [experimental=false] Whether or not to use experimental SSSR.
     * @returns {Array[]} An array containing arrays, each representing a ring from the smallest set of smallest rings in the group.
     */
    static getRings(graph, experimental = false) {
      let adjacencyMatrix = graph.getComponentsAdjacencyMatrix();
      if (adjacencyMatrix.length === 0) {
        return [];
      }
      let connectedComponents = Graph.getConnectedComponents(adjacencyMatrix);
      let rings = [];
      for (let i = 0; i < connectedComponents.length; i++) {
        let connectedComponent = connectedComponents[i];
        let ccAdjacencyMatrix = graph.getSubgraphAdjacencyMatrix([...connectedComponent]);
        let arrBondCount = new Uint16Array(ccAdjacencyMatrix.length);
        let arrRingCount = new Uint16Array(ccAdjacencyMatrix.length);
        for (let j = 0; j < ccAdjacencyMatrix.length; j++) {
          arrRingCount[j] = 0;
          arrBondCount[j] = 0;
          for (let k = 0; k < ccAdjacencyMatrix[j].length; k++) {
            arrBondCount[j] += ccAdjacencyMatrix[j][k];
          }
        }
        let nEdges = 0;
        for (let j = 0; j < ccAdjacencyMatrix.length; j++) {
          for (let k = j + 1; k < ccAdjacencyMatrix.length; k++) {
            nEdges += ccAdjacencyMatrix[j][k];
          }
        }
        let nSssr = nEdges - ccAdjacencyMatrix.length + 1;
        let allThree = true;
        for (let j = 0; j < arrBondCount.length; j++) {
          if (arrBondCount[j] !== 3) {
            allThree = false;
          }
        }
        if (allThree) {
          nSssr = 2 + nEdges - ccAdjacencyMatrix.length;
        }
        if (nSssr === 1) {
          rings.push([...connectedComponent]);
          continue;
        }
        if (experimental) {
          nSssr = 999;
        }
        let { d, pe, pe_prime } = _SSSR.getPathIncludedDistanceMatrices(ccAdjacencyMatrix);
        let c = _SSSR.getRingCandidates(d, pe, pe_prime);
        let sssr = _SSSR.getSSSR(c, d, ccAdjacencyMatrix, pe, pe_prime, arrBondCount, arrRingCount, nSssr);
        if (sssr.length < nSssr) {
          let missing = _SSSR.findMissingRings(ccAdjacencyMatrix, sssr, nSssr);
          for (let j = 0; j < missing.length; j++) {
            sssr.push(missing[j]);
          }
        }
        for (let j = 0; j < sssr.length; j++) {
          let ring = Array(sssr[j].size);
          let index = 0;
          for (let val of sssr[j]) {
            ring[index++] = connectedComponent[val];
          }
          rings.push(ring);
        }
      }
      return rings;
    }
    /**
     * Creates a printable string from a matrix (2D array).
     *
     * @param {Array[]} matrix A 2D array.
     * @returns {String} A string representing the matrix.
     */
    static matrixToString(matrix) {
      let str = "";
      for (let i = 0; i < matrix.length; i++) {
        for (let j = 0; j < matrix[i].length; j++) {
          str += matrix[i][j] + " ";
        }
        str += "\n";
      }
      return str;
    }
    /**
     * Returnes the two path-included distance matrices used to find the sssr.
     *
     * @param {Array[]} adjacencyMatrix An adjacency matrix.
     * @returns {Object} The path-included distance matrices. { p1, p2 }
     */
    static getPathIncludedDistanceMatrices(adjacencyMatrix) {
      let length = adjacencyMatrix.length;
      let d = Array(length);
      let pe = Array(length);
      let pe_prime = Array(length);
      var i = 0;
      var j = 0;
      var k = 0;
      var l = 0;
      var m = 0;
      var n = 0;
      i = length;
      while (i--) {
        d[i] = Array(length);
        pe[i] = Array(length);
        pe_prime[i] = Array(length);
        j = length;
        while (j--) {
          d[i][j] = i === j || adjacencyMatrix[i][j] === 1 ? adjacencyMatrix[i][j] : Number.POSITIVE_INFINITY;
          if (d[i][j] === 1) {
            pe[i][j] = [[[i, j]]];
          } else {
            pe[i][j] = [];
          }
          pe_prime[i][j] = [];
        }
      }
      k = length;
      while (k--) {
        i = length;
        while (i--) {
          j = length;
          while (j--) {
            const previousPathLength = d[i][j];
            const newPathLength = d[i][k] + d[k][j];
            if (previousPathLength > newPathLength) {
              if (previousPathLength === newPathLength + 1) {
                pe_prime[i][j] = [pe[i][j].length];
                l = pe[i][j].length;
                while (l--) {
                  pe_prime[i][j][l] = [pe[i][j][l].length];
                  m = pe[i][j][l].length;
                  while (m--) {
                    pe_prime[i][j][l][m] = [pe[i][j][l][m].length];
                    n = pe[i][j][l][m].length;
                    while (n--) {
                      pe_prime[i][j][l][m][n] = [pe[i][j][l][m][0], pe[i][j][l][m][1]];
                    }
                  }
                }
              } else {
                pe_prime[i][j] = [];
              }
              d[i][j] = newPathLength;
              pe[i][j] = [[]];
              l = pe[i][k][0].length;
              while (l--) {
                pe[i][j][0].push(pe[i][k][0][l]);
              }
              l = pe[k][j][0].length;
              while (l--) {
                pe[i][j][0].push(pe[k][j][0][l]);
              }
            } else if (previousPathLength === newPathLength) {
              if (pe[i][k].length && pe[k][j].length) {
                if (pe[i][j].length) {
                  let tmp = [];
                  l = pe[i][k][0].length;
                  while (l--) {
                    tmp.push(pe[i][k][0][l]);
                  }
                  l = pe[k][j][0].length;
                  while (l--) {
                    tmp.push(pe[k][j][0][l]);
                  }
                  pe[i][j].push(tmp);
                } else {
                  let tmp = [];
                  l = pe[i][k][0].length;
                  while (l--) {
                    tmp.push(pe[i][k][0][l]);
                  }
                  l = pe[k][j][0].length;
                  while (l--) {
                    tmp.push(pe[k][j][0][l]);
                  }
                  pe[i][j][0] = tmp;
                }
              }
            } else if (previousPathLength === newPathLength - 1) {
              if (pe_prime[i][j].length) {
                let tmp = [];
                l = pe[i][k][0].length;
                while (l--) {
                  tmp.push(pe[i][k][0][l]);
                }
                l = pe[k][j][0].length;
                while (l--) {
                  tmp.push(pe[k][j][0][l]);
                }
                pe_prime[i][j].push(tmp);
              } else {
                let tmp = [];
                l = pe[i][k][0].length;
                while (l--) {
                  tmp.push(pe[i][k][0][l]);
                }
                l = pe[k][j][0].length;
                while (l--) {
                  tmp.push(pe[k][j][0][l]);
                }
                pe_prime[i][j][0] = tmp;
              }
            }
          }
        }
      }
      return {
        d,
        pe,
        pe_prime
      };
    }
    /**
     * Get the ring candidates from the path-included distance matrices.
     *
     * @param {Array[]} d The distance matrix.
     * @param {Array[]} pe A matrix containing the shortest paths.
     * @param {Array[]} pe_prime A matrix containing the shortest paths + one vertex.
     * @returns {Array[]} The ring candidates.
     */
    static getRingCandidates(d, pe, pe_prime) {
      let length = d.length;
      let candidates = [];
      let c = 0;
      for (let i = 0; i < length; i++) {
        for (let j = 0; j < length; j++) {
          if (d[i][j] === 0 || pe[i][j].length === 1 && pe_prime[i][j] === 0) {
            continue;
          } else {
            if (pe_prime[i][j].length !== 0) {
              c = 2 * (d[i][j] + 0.5);
            } else {
              c = 2 * d[i][j];
            }
            if (c !== Infinity) {
              candidates.push([c, pe[i][j], pe_prime[i][j]]);
            }
          }
        }
      }
      candidates.sort(function(a, b) {
        return a[0] - b[0];
      });
      return candidates;
    }
    /**
     * Searches the candidates for the smallest set of smallest rings.
     *
     * @param {Array[]} c The candidates.
     * @param {Array[]} d The distance matrix.
     * @param {Array[]} adjacencyMatrix An adjacency matrix.
     * @param {Array[]} pe A matrix containing the shortest paths.
     * @param {Array[]} pe_prime A matrix containing the shortest paths + one vertex.
     * @param {Uint16Array} arrBondCount A matrix containing the bond count of each vertex.
     * @param {Uint16Array} arrRingCount A matrix containing the number of rings associated with each vertex.
     * @param {Number} nsssr The theoretical number of rings in the graph.
     * @returns {Set[]} The smallest set of smallest rings.
     */
    static getSSSR(c, d, adjacencyMatrix, pe, pe_prime, arrBondCount, arrRingCount, nsssr) {
      let cSssr = [];
      let allBonds = [];
      for (let i = 0; i < c.length; i++) {
        if (c[i][0] % 2 !== 0) {
          for (let j = 0; j < c[i][2].length; j++) {
            let bonds = c[i][1][0].concat(c[i][2][j]);
            for (let k = 0; k < bonds.length; k++) {
              if (bonds[k][0].constructor === Array) bonds[k] = bonds[k][0];
            }
            let atoms = _SSSR.bondsToAtoms(bonds);
            if (_SSSR.getBondCount(atoms, adjacencyMatrix) === atoms.size && !_SSSR.pathSetsContain(cSssr, atoms, bonds, allBonds, arrBondCount, arrRingCount)) {
              cSssr.push(atoms);
              allBonds = allBonds.concat(bonds);
            }
            if (cSssr.length > nsssr) {
              return cSssr;
            }
          }
        } else {
          for (let j = 0; j < c[i][1].length - 1; j++) {
            let bonds = c[i][1][j].concat(c[i][1][j + 1]);
            for (let k = 0; k < bonds.length; k++) {
              if (bonds[k][0].constructor === Array) bonds[k] = bonds[k][0];
            }
            let atoms = _SSSR.bondsToAtoms(bonds);
            if (_SSSR.getBondCount(atoms, adjacencyMatrix) === atoms.size && !_SSSR.pathSetsContain(cSssr, atoms, bonds, allBonds, arrBondCount, arrRingCount)) {
              cSssr.push(atoms);
              allBonds = allBonds.concat(bonds);
            }
            if (cSssr.length > nsssr) {
              return cSssr;
            }
          }
        }
      }
      return cSssr;
    }
    /**
     * Returns the number of edges in a graph defined by an adjacency matrix.
     *
     * @param {Array[]} adjacencyMatrix An adjacency matrix.
     * @returns {Number} The number of edges in the graph defined by the adjacency matrix.
     */
    static getEdgeCount(adjacencyMatrix) {
      let edgeCount = 0;
      let length = adjacencyMatrix.length;
      var i = length - 1;
      while (i--) {
        var j = length;
        while (j--) {
          if (adjacencyMatrix[i][j] === 1) {
            edgeCount++;
          }
        }
      }
      return edgeCount;
    }
    /**
     * Returns an edge list constructed form an adjacency matrix.
     *
     * @param {Array[]} adjacencyMatrix An adjacency matrix.
     * @returns {Array[]} An edge list. E.g. [ [ 0, 1 ], ..., [ 16, 2 ] ]
     */
    static getEdgeList(adjacencyMatrix) {
      let length = adjacencyMatrix.length;
      let edgeList = [];
      var i = length - 1;
      while (i--) {
        var j = length;
        while (j--) {
          if (adjacencyMatrix[i][j] === 1) {
            edgeList.push([i, j]);
          }
        }
      }
      return edgeList;
    }
    /**
     * Return a set of vertex indices contained in an array of bonds.
     *
     * @param {Array} bonds An array of bonds. A bond is defined as [ sourceVertexId, targetVertexId ].
     * @returns {Set<Number>} An array of vertices.
     */
    static bondsToAtoms(bonds) {
      let atoms = /* @__PURE__ */ new Set();
      var i = bonds.length;
      while (i--) {
        atoms.add(bonds[i][0]);
        atoms.add(bonds[i][1]);
      }
      return atoms;
    }
    /**
    * Returns the number of bonds within a set of atoms.
    *
    * @param {Set<Number>} atoms An array of atom ids.
    * @param {Array[]} adjacencyMatrix An adjacency matrix.
    * @returns {Number} The number of bonds in a set of atoms.
    */
    static getBondCount(atoms, adjacencyMatrix) {
      let count = 0;
      for (let u of atoms) {
        for (let v of atoms) {
          if (u === v) {
            continue;
          }
          count += adjacencyMatrix[u][v];
        }
      }
      return count / 2;
    }
    /**
     * Checks whether or not a given path already exists in an array of paths.
     *
     * @param {Set[]} pathSets An array of sets each representing a path.
     * @param {Set<Number>} pathSet A set representing a path.
     * @param {Array[]} bonds The bonds associated with the current path.
     * @param {Array[]} allBonds All bonds currently associated with rings in the SSSR set.
     * @param {Uint16Array} arrBondCount A matrix containing the bond count of each vertex.
     * @param {Uint16Array} arrRingCount A matrix containing the number of rings associated with each vertex.
     * @returns {Boolean} A boolean indicating whether or not a give path is contained within a set.
     */
    static pathSetsContain(pathSets, pathSet, bonds, allBonds, arrBondCount, arrRingCount) {
      var i = pathSets.length;
      while (i--) {
        if (_SSSR.isSupersetOf(pathSet, pathSets[i])) {
          return true;
        }
        if (pathSets[i].size !== pathSet.size) {
          continue;
        }
        if (_SSSR.areSetsEqual(pathSets[i], pathSet)) {
          return true;
        }
      }
      let count = 0;
      let allContained = false;
      i = bonds.length;
      while (i--) {
        var j = allBonds.length;
        while (j--) {
          if (bonds[i][0] === allBonds[j][0] && bonds[i][1] === allBonds[j][1] || bonds[i][1] === allBonds[j][0] && bonds[i][0] === allBonds[j][1]) {
            count++;
          }
          if (count === bonds.length) {
            allContained = true;
          }
        }
      }
      let specialCase = false;
      if (allContained) {
        for (let element of pathSet) {
          if (arrRingCount[element] < arrBondCount[element]) {
            specialCase = true;
            break;
          }
        }
      }
      if (allContained && !specialCase) {
        return true;
      }
      for (let element of pathSet) {
        arrRingCount[element]++;
      }
      return false;
    }
    /**
     * Checks whether or not two sets are equal (contain the same elements).
     *
     * @param {Set<Number>} setA A set.
     * @param {Set<Number>} setB A set.
     * @returns {Boolean} A boolean indicating whether or not the two sets are equal.
     */
    static areSetsEqual(setA, setB) {
      if (setA.size !== setB.size) {
        return false;
      }
      for (let element of setA) {
        if (!setB.has(element)) {
          return false;
        }
      }
      return true;
    }
    /**
     * Checks whether or not a set (setA) is a superset of another set (setB).
     *
     * @param {Set<Number>} setA A set.
     * @param {Set<Number>} setB A set.
     * @returns {Boolean} A boolean indicating whether or not setB is a superset of setA.
     */
    static isSupersetOf(setA, setB) {
      for (let element of setB) {
        if (!setA.has(element)) {
          return false;
        }
      }
      return true;
    }
    /**
     * Find missing rings using BFS when the main SSSR algorithm falls short.
     * For each edge not covered by existing rings, find the shortest cycle
     * containing that edge.
     *
     * @static
     * @param {Array[]} adjacencyMatrix 
     * @param {Set[]} existingRings The rings already found by the SSSR algorithm.
     * @param {Number} nSssr The expected number of rings.
     * @returns {Set[]} newly found rings 
     */
    static findMissingRings(adjacencyMatrix, existingRings, nSssr) {
      let length = adjacencyMatrix.length;
      let newRings = [];
      let coveredEdges = /* @__PURE__ */ new Set();
      for (let ring of existingRings) {
        let members = [...ring];
        for (let k = 0; k < members.length; k++) {
          for (let l = k + 1; l < members.length; l++) {
            if (adjacencyMatrix[members[k]][members[l]] === 1) {
              let a = Math.min(members[k], members[l]);
              let b = Math.max(members[k], members[l]);
              coveredEdges.add(a + "," + b);
            }
          }
        }
      }
      for (let u = 0; u < length; u++) {
        for (let v = u + 1; v < length; v++) {
          if (adjacencyMatrix[u][v] !== 1) continue;
          let edgeKey = u + "," + v;
          if (coveredEdges.has(edgeKey)) continue;
          let cycle = _SSSR.bfsShortestCycle(adjacencyMatrix, u, v, length);
          if (cycle !== null) {
            let ringSet = new Set(cycle);
            let isDuplicate = false;
            for (let existing of existingRings) {
              if (_SSSR.areSetsEqual(ringSet, existing)) {
                isDuplicate = true;
                break;
              }
            }
            for (let nr of newRings) {
              if (_SSSR.areSetsEqual(ringSet, nr)) {
                isDuplicate = true;
                break;
              }
            }
            if (!isDuplicate) {
              newRings.push(ringSet);
              let members = [...ringSet];
              for (let k = 0; k < members.length; k++) {
                for (let l = k + 1; l < members.length; l++) {
                  if (adjacencyMatrix[members[k]][members[l]] === 1) {
                    let a = Math.min(members[k], members[l]);
                    let b = Math.max(members[k], members[l]);
                    coveredEdges.add(a + "," + b);
                  }
                }
              }
              if (existingRings.length + newRings.length >= nSssr) {
                return newRings;
              }
            }
          }
        }
      }
      return newRings;
    }
    /**
     * BFS to find shortest path from u to v without using the direct u-v edge.
     * Returns the cycle as an array of vertex indices, or null if no path exists.
     *
     * @static
     * @param {Array[]} adjacencyMatrix The adjacency matrix.
     * @param {Number} u Source vertex.
     * @param {Number} v Target vertex.
     * @param {Number} length Number of vertices.
     * @returns {Number[]|null} The cycle vertices, or null.
     */
    static bfsShortestCycle(adjacencyMatrix, u, v, length) {
      let visited = new Array(length).fill(false);
      let parent = new Array(length).fill(-1);
      let queue = [u];
      visited[u] = true;
      while (queue.length > 0) {
        let current = queue.shift();
        for (let neighbor = 0; neighbor < length; neighbor++) {
          if (adjacencyMatrix[current][neighbor] !== 1) continue;
          if (current === u && neighbor === v) continue;
          if (current === v && neighbor === u) continue;
          if (neighbor === v) {
            let path = [v];
            let node = current;
            while (node !== -1) {
              path.push(node);
              node = parent[node];
            }
            return path;
          }
          if (!visited[neighbor]) {
            visited[neighbor] = true;
            parent[neighbor] = current;
            queue.push(neighbor);
          }
        }
      }
      return null;
    }
  };

  // node_modules/smiles-drawer/src/DrawerBase.js
  var DrawerBase = class {
    /**
     * The constructor for the class SmilesDrawer.
     *
     * @param {Object} options An object containing custom values for different options. It is merged with the default options.
     */
    constructor(options) {
      this.graph = null;
      this.doubleBondConfigCount = 0;
      this.doubleBondConfig = null;
      this.ringIdCounter = 0;
      this.ringConnectionIdCounter = 0;
      this.canvasWrapper = null;
      this.totalOverlapScore = 0;
      this.defaultOptions = {
        width: 500,
        height: 500,
        scale: 0,
        bondThickness: 1,
        bondLength: 30,
        shortBondLength: 0.8,
        bondSpacing: 0.17 * 30,
        atomVisualization: "default",
        isomeric: true,
        debug: false,
        terminalCarbons: false,
        explicitHydrogens: true,
        overlapSensitivity: 0.42,
        overlapResolutionIterations: 1,
        compactDrawing: true,
        fontFamily: "Arial, Helvetica, sans-serif",
        fontSizeLarge: 11,
        fontSizeSmall: 3,
        padding: 10,
        experimentalSSSR: false,
        kkThreshold: 0.1,
        kkInnerThreshold: 0.1,
        kkMaxIteration: 2e4,
        kkMaxInnerIteration: 50,
        kkMaxEnergy: 1e9,
        weights: {
          colormap: null,
          additionalPadding: 20,
          sigma: 10,
          interval: 0,
          opacity: 1
        },
        themes: {
          "dark": {
            FOREGROUND: "#ffffff",
            BACKGROUND: "#141414",
            C: "#ffffff",
            O: "#e74c3c",
            N: "#3498db",
            F: "#27ae60",
            CL: "#16a085",
            BR: "#d35400",
            I: "#8e44ad",
            P: "#d35400",
            S: "#f1c40f",
            B: "#e67e22",
            SI: "#e67e22",
            H: "#aaaaaa"
          },
          "light": {
            FOREGROUND: "#222222",
            BACKGROUND: "#ffffff",
            C: "#222222",
            O: "#e74c3c",
            N: "#3498db",
            F: "#27ae60",
            CL: "#16a085",
            BR: "#d35400",
            I: "#8e44ad",
            P: "#d35400",
            S: "#f1c40f",
            B: "#e67e22",
            SI: "#e67e22",
            H: "#666666"
          },
          "oldschool": {
            FOREGROUND: "#000000",
            BACKGROUND: "#ffffff",
            C: "#000000",
            O: "#000000",
            N: "#000000",
            F: "#000000",
            CL: "#000000",
            BR: "#000000",
            I: "#000000",
            P: "#000000",
            S: "#000000",
            B: "#000000",
            SI: "#000000",
            H: "#000000"
          },
          "solarized": {
            FOREGROUND: "#586e75",
            BACKGROUND: "#eee8d5",
            C: "#586e75",
            O: "#dc322f",
            N: "#268bd2",
            F: "#859900",
            CL: "#16a085",
            BR: "#cb4b16",
            I: "#6c71c4",
            P: "#d33682",
            S: "#b58900",
            B: "#2aa198",
            SI: "#2aa198",
            H: "#657b83"
          },
          "solarized-dark": {
            FOREGROUND: "#93a1a1",
            BACKGROUND: "#073642",
            C: "#93a1a1",
            O: "#dc322f",
            N: "#268bd2",
            F: "#859900",
            CL: "#16a085",
            BR: "#cb4b16",
            I: "#6c71c4",
            P: "#d33682",
            S: "#b58900",
            B: "#2aa198",
            SI: "#2aa198",
            H: "#839496"
          },
          "matrix": {
            FOREGROUND: "#678c61",
            BACKGROUND: "#ffffff",
            C: "#678c61",
            O: "#2fc079",
            N: "#4f7e7e",
            F: "#90d762",
            CL: "#82d967",
            BR: "#23755a",
            I: "#409931",
            P: "#c1ff8a",
            S: "#faff00",
            B: "#50b45a",
            SI: "#409931",
            H: "#426644"
          },
          "github": {
            FOREGROUND: "#24292f",
            BACKGROUND: "#ffffff",
            C: "#24292f",
            O: "#cf222e",
            N: "#0969da",
            F: "#2da44e",
            CL: "#6fdd8b",
            BR: "#bc4c00",
            I: "#8250df",
            P: "#bf3989",
            S: "#d4a72c",
            B: "#fb8f44",
            SI: "#bc4c00",
            H: "#57606a"
          },
          "carbon": {
            FOREGROUND: "#161616",
            BACKGROUND: "#ffffff",
            C: "#161616",
            O: "#da1e28",
            N: "#0f62fe",
            F: "#198038",
            CL: "#007d79",
            BR: "#fa4d56",
            I: "#8a3ffc",
            P: "#ff832b",
            S: "#f1c21b",
            B: "#8a3800",
            SI: "#e67e22",
            H: "#525252"
          },
          "cyberpunk": {
            FOREGROUND: "#ea00d9",
            BACKGROUND: "#ffffff",
            C: "#ea00d9",
            O: "#ff3131",
            N: "#0abdc6",
            F: "#00ff9f",
            CL: "#00fe00",
            BR: "#fe9f20",
            I: "#ff00ff",
            P: "#fe7f00",
            S: "#fcee0c",
            B: "#ff00ff",
            SI: "#ffffff",
            H: "#913cb1"
          },
          "gruvbox": {
            FOREGROUND: "#665c54",
            BACKGROUND: "#fbf1c7",
            C: "#665c54",
            O: "#cc241d",
            N: "#458588",
            F: "#98971a",
            CL: "#79740e",
            BR: "#d65d0e",
            I: "#b16286",
            P: "#af3a03",
            S: "#d79921",
            B: "#689d6a",
            SI: "#427b58",
            H: "#7c6f64"
          },
          "gruvbox-dark": {
            FOREGROUND: "#ebdbb2",
            BACKGROUND: "#282828",
            C: "#ebdbb2",
            O: "#cc241d",
            N: "#458588",
            F: "#98971a",
            CL: "#b8bb26",
            BR: "#d65d0e",
            I: "#b16286",
            P: "#fe8019",
            S: "#d79921",
            B: "#8ec07c",
            SI: "#83a598",
            H: "#bdae93"
          },
          "custom": {
            FOREGROUND: "#222222",
            BACKGROUND: "#ffffff",
            C: "#222222",
            O: "#e74c3c",
            N: "#3498db",
            F: "#27ae60",
            CL: "#16a085",
            BR: "#d35400",
            I: "#8e44ad",
            P: "#d35400",
            S: "#f1c40f",
            B: "#e67e22",
            SI: "#e67e22",
            H: "#666666"
          }
        }
      };
      this.opts = Options.extend(true, this.defaultOptions, options);
      this.opts.halfBondSpacing = this.opts.bondSpacing / 2;
      this.opts.bondLengthSq = this.opts.bondLength * this.opts.bondLength;
      this.opts.halfFontSizeLarge = this.opts.fontSizeLarge / 2;
      this.opts.quarterFontSizeLarge = this.opts.fontSizeLarge / 4;
      this.opts.fifthFontSizeSmall = this.opts.fontSizeSmall / 5;
      this.theme = this.opts.themes.dark;
    }
    /**
     * Draws the parsed smiles data to a canvas element.
     *
     * @param {Object} data The tree returned by the smiles parser.
     * @param {(String|HTMLCanvasElement)} target The id of the HTML canvas element the structure is drawn to - or the element itself.
     * @param {String} themeName='dark' The name of the theme to use. Built-in themes are 'light' and 'dark'.
     * @param {Boolean} infoOnly=false Only output info on the molecule without drawing anything to the canvas.
     */
    draw(data, target, themeName = "light", infoOnly = false) {
      this.initDraw(data, themeName, infoOnly);
      if (!this.infoOnly) {
        this.themeManager = new ThemeManager(this.opts.themes, themeName);
        this.canvasWrapper = new CanvasWrapper(target, this.themeManager, this.opts);
      }
      if (!infoOnly) {
        this.processGraph();
        this.canvasWrapper.scale(this.graph.vertices);
        this.drawEdges(this.opts.debug);
        this.drawVertices(this.opts.debug);
        this.canvasWrapper.reset();
        if (this.opts.debug) {
          console.debug("DrawerBase::draw()", {
            graph: this.graph,
            rings: this.rings,
            ringConnections: this.ringConnections
          });
        }
      }
    }
    /**
     * Returns the number of rings this edge is a part of.
     *
     * @param {Number} edgeId The id of an edge.
     * @returns {Number} The number of rings the provided edge is part of.
     */
    edgeRingCount(edgeId) {
      let edge = this.graph.edges[edgeId];
      let a = this.graph.vertices[edge.sourceId];
      let b = this.graph.vertices[edge.targetId];
      return Math.min(a.value.rings.length, b.value.rings.length);
    }
    /**
     * Returns an array containing the bridged rings associated with this  molecule.
     *
     * @returns {Ring[]} An array containing all bridged rings associated with this molecule.
     */
    getBridgedRings() {
      return this.rings.filter((ring) => ring.isBridged);
    }
    /**
     * Returns an array containing all fused rings associated with this molecule.
     *
     * @returns {Ring[]} An array containing all fused rings associated with this molecule.
     */
    getFusedRings() {
      return this.rings.filter((ring) => ring.isFused);
    }
    /**
     * Returns an array containing all spiros associated with this molecule.
     *
     * @returns {Ring[]} An array containing all spiros associated with this molecule.
     */
    getSpiros() {
      return this.rings.filter((ring) => ring.isSpiro);
    }
    /**
     * Returns a string containing a semicolon and new-line separated list of ring properties: Id; Members Count; Neighbours Count; IsSpiro; IsFused; IsBridged; Ring Count (subrings of bridged rings)
     *
     * @returns {String} A string as described in the method description.
     */
    printRingInfo() {
      let result = "";
      for (let i = 0; i < this.rings.length; i++) {
        const ring = this.rings[i];
        result += ring.id + ";";
        result += ring.members.length + ";";
        result += ring.neighbours.length + ";";
        result += ring.isSpiro ? "true;" : "false;";
        result += ring.isFused ? "true;" : "false;";
        result += ring.isBridged ? "true;" : "false;";
        result += ring.rings.length + ";";
        result += "\n";
      }
      return result;
    }
    /**
     * Rotates the drawing to make the widest dimension horizontal.
     */
    rotateDrawing() {
      let a = 0;
      let b = 0;
      let maxDist = 0;
      for (let i = 0; i < this.graph.vertices.length; i++) {
        let vertexA = this.graph.vertices[i];
        if (!vertexA.value.isDrawn) {
          continue;
        }
        for (let j = i + 1; j < this.graph.vertices.length; j++) {
          let vertexB = this.graph.vertices[j];
          if (!vertexB.value.isDrawn) {
            continue;
          }
          let dist = vertexA.position.distanceSq(vertexB.position);
          if (dist > maxDist) {
            maxDist = dist;
            a = i;
            b = j;
          }
        }
      }
      let angle = -Vector2.subtract(this.graph.vertices[a].position, this.graph.vertices[b].position).angle();
      if (!isNaN(angle)) {
        let remainder = angle % 0.523599;
        if (remainder < 0.2617995) {
          angle = angle - remainder;
        } else {
          angle += 0.523599 - remainder;
        }
        for (let i = 0; i < this.graph.vertices.length; i++) {
          if (i === b) {
            continue;
          }
          this.graph.vertices[i].position.rotateAround(angle, this.graph.vertices[b].position);
        }
        for (let i = 0; i < this.rings.length; i++) {
          this.rings[i].center.rotateAround(angle, this.graph.vertices[b].position);
        }
      }
    }
    /**
     * Returns the total overlap score of the current molecule.
     *
     * @returns {Number} The overlap score.
     */
    getTotalOverlapScore() {
      return this.totalOverlapScore;
    }
    /**
     * Returns the ring count of the current molecule.
     *
     * @returns {Number} The ring count.
     */
    getRingCount() {
      return this.rings.length;
    }
    /**
     * Checks whether or not the current molecule  a bridged ring.
     *
     * @returns {Boolean} A boolean indicating whether or not the current molecule  a bridged ring.
     */
    hasBridgedRing() {
      return this.bridgedRing;
    }
    /**
     * Returns the number of heavy atoms (non-hydrogen) in the current molecule.
     *
     * @returns {Number} The heavy atom count.
     */
    getHeavyAtomCount() {
      let hac = 0;
      for (let i = 0; i < this.graph.vertices.length; i++) {
        if (this.graph.vertices[i].value.element !== "H") {
          hac++;
        }
      }
      return hac;
    }
    /**
     * Returns the molecular formula of the loaded molecule as a string.
     *
     * @returns {String} The molecular formula.
     */
    getMolecularFormula(data = null) {
      let molecularFormula = "";
      let counts = /* @__PURE__ */ new Map();
      let graph = data === null ? this.graph : new Graph(data, this.opts.isomeric);
      for (let i = 0; i < graph.vertices.length; i++) {
        let atom = graph.vertices[i].value;
        if (counts.has(atom.element)) {
          counts.set(atom.element, counts.get(atom.element) + 1);
        } else {
          counts.set(atom.element, 1);
        }
        if (atom.bracket && !atom.bracket.chirality) {
          if (counts.has("H")) {
            counts.set("H", counts.get("H") + atom.bracket.hcount);
          } else {
            counts.set("H", atom.bracket.hcount);
          }
        }
        if (!atom.bracket) {
          let nHydrogens = Atom.maxBonds[atom.element] - atom.bondCount;
          if (atom.isPartOfAromaticRing) {
            nHydrogens--;
          }
          if (counts.has("H")) {
            counts.set("H", counts.get("H") + nHydrogens);
          } else {
            counts.set("H", nHydrogens);
          }
        }
      }
      if (counts.has("C")) {
        let count = counts.get("C");
        molecularFormula += "C" + (count > 1 ? count : "");
        counts.delete("C");
      }
      if (counts.has("H")) {
        let count = counts.get("H");
        molecularFormula += "H" + (count > 1 ? count : "");
        counts.delete("H");
      }
      let elements = Object.keys(Atom.atomicNumbers).sort();
      elements.map((e) => {
        if (counts.has(e)) {
          let count = counts.get(e);
          molecularFormula += e + (count > 1 ? count : "");
        }
      });
      return molecularFormula;
    }
    /**
     * Returns the type of the ringbond (e.g. '=' for a double bond). The ringbond represents the break in a ring introduced when creating the MST. If the two vertices supplied as arguments are not part of a common ringbond, the method returns null.
     *
     * @param {Vertex} vertexA A vertex.
     * @param {Vertex} vertexB A vertex.
     * @returns {(String|null)} Returns the ringbond type or null, if the two supplied vertices are not connected by a ringbond.
     */
    getRingbondType(vertexA, vertexB) {
      if (vertexA.value.getRingbondCount() < 1 || vertexB.value.getRingbondCount() < 1) {
        return null;
      }
      for (let i = 0; i < vertexA.value.ringbonds.length; i++) {
        for (let j = 0; j < vertexB.value.ringbonds.length; j++) {
          if (vertexA.value.ringbonds[i].id === vertexB.value.ringbonds[j].id) {
            if (vertexA.value.ringbonds[i].bondType === "-") {
              return vertexB.value.ringbonds[j].bond;
            } else {
              return vertexA.value.ringbonds[i].bond;
            }
          }
        }
      }
      return null;
    }
    initDraw(data, themeName, infoOnly, highlight_atoms) {
      this.data = data;
      this.infoOnly = infoOnly;
      this.ringIdCounter = 0;
      this.ringConnectionIdCounter = 0;
      this.graph = new Graph(data, this.opts.isomeric);
      this.rings = [];
      this.ringConnections = [];
      this.originalRings = [];
      this.originalRingConnections = [];
      this.bridgedRing = false;
      this.doubleBondConfigCount = null;
      this.doubleBondConfig = null;
      this.highlight_atoms = highlight_atoms;
      this.initRings();
      this.initHydrogens();
    }
    processGraph() {
      this.position();
      this.restoreRingInformation();
      this.resolvePrimaryOverlaps();
      let overlapScore = this.getOverlapScore();
      this.totalOverlapScore = this.getOverlapScore().total;
      for (let o = 0; o < this.opts.overlapResolutionIterations; o++) {
        for (let i = 0; i < this.graph.edges.length; i++) {
          let edge = this.graph.edges[i];
          if (this.isEdgeRotatable(edge)) {
            let subTreeDepthA = this.graph.getTreeDepth(edge.sourceId, edge.targetId);
            let subTreeDepthB = this.graph.getTreeDepth(edge.targetId, edge.sourceId);
            let a = edge.targetId;
            let b = edge.sourceId;
            if (subTreeDepthA > subTreeDepthB) {
              a = edge.sourceId;
              b = edge.targetId;
            }
            let subTreeOverlap = this.getSubtreeOverlapScore(b, a, overlapScore.vertexScores);
            if (subTreeOverlap.value > this.opts.overlapSensitivity) {
              let vertexA = this.graph.vertices[a];
              let vertexB = this.graph.vertices[b];
              let neighboursB = vertexB.getNeighbours(a);
              if (neighboursB.length === 1) {
                let neighbour = this.graph.vertices[neighboursB[0]];
                let angle = neighbour.position.getRotateAwayFromAngle(vertexA.position, vertexB.position, MathHelper.toRad(120));
                this.rotateSubtree(neighbour.id, vertexB.id, angle, vertexB.position);
                let newTotalOverlapScore = this.getOverlapScore().total;
                if (newTotalOverlapScore > this.totalOverlapScore) {
                  this.rotateSubtree(neighbour.id, vertexB.id, -angle, vertexB.position);
                } else {
                  this.totalOverlapScore = newTotalOverlapScore;
                }
              } else if (neighboursB.length === 2) {
                if (vertexB.value.rings.length !== 0 && vertexA.value.rings.length !== 0) {
                  continue;
                }
                let neighbourA = this.graph.vertices[neighboursB[0]];
                let neighbourB = this.graph.vertices[neighboursB[1]];
                if (neighbourA.value.rings.length === 1 && neighbourB.value.rings.length === 1) {
                  if (neighbourA.value.rings[0] !== neighbourB.value.rings[0]) {
                    continue;
                  }
                } else if (neighbourA.value.rings.length !== 0 || neighbourB.value.rings.length !== 0) {
                  continue;
                } else {
                  let angleA = neighbourA.position.getRotateAwayFromAngle(vertexA.position, vertexB.position, MathHelper.toRad(120));
                  let angleB = neighbourB.position.getRotateAwayFromAngle(vertexA.position, vertexB.position, MathHelper.toRad(120));
                  this.rotateSubtree(neighbourA.id, vertexB.id, angleA, vertexB.position);
                  this.rotateSubtree(neighbourB.id, vertexB.id, angleB, vertexB.position);
                  let newTotalOverlapScore = this.getOverlapScore().total;
                  if (newTotalOverlapScore > this.totalOverlapScore) {
                    this.rotateSubtree(neighbourA.id, vertexB.id, -angleA, vertexB.position);
                    this.rotateSubtree(neighbourB.id, vertexB.id, -angleB, vertexB.position);
                  } else {
                    this.totalOverlapScore = newTotalOverlapScore;
                  }
                }
              }
              overlapScore = this.getOverlapScore();
            }
          }
        }
      }
      this.resolveSecondaryOverlaps(overlapScore.scores);
      if (this.opts.isomeric) {
        this.annotateStereochemistry();
      }
      if (this.opts.compactDrawing && this.opts.atomVisualization === "default") {
        this.initPseudoElements();
      }
      this.rotateDrawing();
    }
    /**
     * Initializes rings and ringbonds for the current molecule.
     */
    initRings() {
      let openBonds = /* @__PURE__ */ new Map();
      for (let i = this.graph.vertices.length - 1; i >= 0; i--) {
        let vertex = this.graph.vertices[i];
        if (vertex.value.ringbonds.length === 0) {
          continue;
        }
        for (let j = 0; j < vertex.value.ringbonds.length; j++) {
          let ringbondId = vertex.value.ringbonds[j].id;
          let ringbondBond = vertex.value.ringbonds[j].bond;
          if (!openBonds.has(ringbondId)) {
            openBonds.set(ringbondId, [vertex.id, ringbondBond]);
          } else {
            let sourceVertexId = vertex.id;
            let targetVertexId = openBonds.get(ringbondId)[0];
            let targetRingbondBond = openBonds.get(ringbondId)[1];
            let edge = new Edge(sourceVertexId, targetVertexId, 1);
            edge.setBondType(targetRingbondBond || ringbondBond || "-");
            let edgeId = this.graph.addEdge(edge);
            let targetVertex = this.graph.vertices[targetVertexId];
            vertex.addRingbondChild(targetVertexId, j);
            vertex.value.addNeighbouringElement(targetVertex.value.element);
            targetVertex.addRingbondChild(sourceVertexId, j);
            targetVertex.value.addNeighbouringElement(vertex.value.element);
            vertex.edges.push(edgeId);
            targetVertex.edges.push(edgeId);
            openBonds.delete(ringbondId);
          }
        }
      }
      let rings = SSSR.getRings(this.graph, this.opts.experimentalSSSR);
      if (rings === null || rings.length === 0) {
        return;
      }
      for (let i = 0; i < rings.length; i++) {
        let ringVertices = [...rings[i]];
        let ringId = this.addRing(new Ring(ringVertices));
        for (let j = 0; j < ringVertices.length; j++) {
          this.graph.vertices[ringVertices[j]].value.rings.push(ringId);
        }
      }
      for (let i = 0; i < this.rings.length - 1; i++) {
        for (let j = i + 1; j < this.rings.length; j++) {
          let a = this.rings[i];
          let b = this.rings[j];
          let ringConnection = new RingConnection(a, b);
          if (ringConnection.vertices.size > 0) {
            this.addRingConnection(ringConnection);
          }
        }
      }
      for (let i = 0; i < this.rings.length; i++) {
        let ring = this.rings[i];
        ring.neighbours = RingConnection.getNeighbours(this.ringConnections, ring.id);
      }
      for (let i = 0; i < this.rings.length; i++) {
        let ring = this.rings[i];
        this.graph.vertices[ring.members[0]].value.addAnchoredRing(ring.id);
      }
      this.backupRingInformation();
      while (this.rings.length > 0) {
        let id = -1;
        for (let i = 0; i < this.rings.length; i++) {
          let ring2 = this.rings[i];
          if (this.isPartOfBridgedRing(ring2.id) && !ring2.isBridged) {
            id = ring2.id;
          }
        }
        if (id === -1) {
          break;
        }
        let ring = this.getRing(id);
        let involvedRings = this.getBridgedRingRings(ring.id);
        this.bridgedRing = true;
        this.createBridgedRing(involvedRings, ring.members[0]);
        this.bridgedRing = false;
        for (let i = 0; i < involvedRings.length; i++) {
          this.removeRing(involvedRings[i]);
        }
      }
    }
    initHydrogens() {
      if (!this.opts.explicitHydrogens) {
        for (let i = 0; i < this.graph.vertices.length; i++) {
          let vertex = this.graph.vertices[i];
          if (vertex.value.element !== "H") {
            continue;
          }
          let neighbour = this.graph.vertices[vertex.neighbours[0]];
          neighbour.value.hasHydrogen = true;
          if (!neighbour.value.isStereoCenter || neighbour.value.rings.length < 2 && !neighbour.value.bridgedRing || neighbour.value.bridgedRing && neighbour.value.originalRings.length < 2) {
            vertex.value.isDrawn = false;
          }
        }
      }
    }
    /**
     * Returns all rings connected by bridged bonds starting from the ring with the supplied ring id.
     *
     * @param {Number} ringId A ring id.
     * @returns {Number[]} An array containing all ring ids of rings part of a bridged ring system.
     */
    getBridgedRingRings(ringId) {
      let involvedRings = [];
      let recurse = (r) => {
        let ring = this.getRing(r);
        involvedRings.push(r);
        for (let i = 0; i < ring.neighbours.length; i++) {
          let n = ring.neighbours[i];
          if (involvedRings.indexOf(n) === -1 && n !== r && RingConnection.isBridge(this.ringConnections, this.graph.vertices, r, n)) {
            recurse(n);
          }
        }
      };
      recurse(ringId);
      return ArrayHelper.unique(involvedRings);
    }
    /**
     * Checks whether or not a ring is part of a bridged ring.
     *
     * @param {Number} ringId A ring id.
     * @returns {Boolean} A boolean indicating whether or not the supplied ring (by id) is part of a bridged ring system.
     */
    isPartOfBridgedRing(ringId) {
      for (let i = 0; i < this.ringConnections.length; i++) {
        if (this.ringConnections[i].containsRing(ringId) && this.ringConnections[i].isBridge(this.graph.vertices)) {
          return true;
        }
      }
      return false;
    }
    /**
     * Creates a bridged ring.
     *
     * @param {Number[]} ringIds An array of ids of rings involved in the bridged ring.
     * @param {Number} sourceVertexId The vertex id to start the bridged ring discovery from.
     * @returns {Ring} The bridged ring.
     */
    createBridgedRing(ringIds, sourceVertexId) {
      let ringMembers = /* @__PURE__ */ new Set();
      let vertices = /* @__PURE__ */ new Set();
      let neighbours = /* @__PURE__ */ new Set();
      for (let i = 0; i < ringIds.length; i++) {
        let ring2 = this.getRing(ringIds[i]);
        ring2.isPartOfBridged = true;
        for (let j = 0; j < ring2.members.length; j++) {
          vertices.add(ring2.members[j]);
        }
        for (let j = 0; j < ring2.neighbours.length; j++) {
          let id = ring2.neighbours[j];
          if (ringIds.indexOf(id) === -1) {
            neighbours.add(ring2.neighbours[j]);
          }
        }
      }
      let leftovers = /* @__PURE__ */ new Set();
      for (let id of vertices) {
        let vertex = this.graph.vertices[id];
        let intersection = ArrayHelper.intersection(ringIds, vertex.value.rings);
        if (vertex.value.rings.length === 1 || intersection.length === 1) {
          ringMembers.add(vertex.id);
        } else {
          leftovers.add(vertex.id);
        }
      }
      let insideRing = [];
      for (let id of leftovers) {
        let vertex = this.graph.vertices[id];
        let onRing = false;
        for (let j = 0; j < vertex.edges.length; j++) {
          if (this.edgeRingCount(vertex.edges[j]) === 1) {
            onRing = true;
          }
        }
        if (onRing) {
          vertex.value.isBridgeNode = true;
          ringMembers.add(vertex.id);
        } else {
          vertex.value.isBridge = true;
          ringMembers.add(vertex.id);
        }
      }
      let ring = new Ring([...ringMembers]);
      this.addRing(ring);
      ring.isBridged = true;
      ring.neighbours = [...neighbours];
      for (let i = 0; i < ringIds.length; i++) {
        ring.rings.push(this.getRing(ringIds[i]).clone());
      }
      for (let i = 0; i < ring.members.length; i++) {
        this.graph.vertices[ring.members[i]].value.bridgedRing = ring.id;
      }
      for (let i = 0; i < insideRing.length; i++) {
        let vertex = this.graph.vertices[insideRing[i]];
        vertex.value.rings = [];
      }
      for (let id of ringMembers) {
        let vertex = this.graph.vertices[id];
        vertex.value.rings = ArrayHelper.removeAll(vertex.value.rings, ringIds);
        vertex.value.rings.push(ring.id);
      }
      for (let i = 0; i < ringIds.length; i++) {
        for (let j = i + 1; j < ringIds.length; j++) {
          this.removeRingConnectionsBetween(ringIds[i], ringIds[j]);
        }
      }
      for (let id of neighbours) {
        let connections = this.getRingConnections(id, ringIds);
        for (let j = 0; j < connections.length; j++) {
          this.getRingConnection(connections[j]).updateOther(ring.id, id);
        }
        this.getRing(id).neighbours.push(ring.id);
      }
      return ring;
    }
    /**
     * Checks whether or not two vertices are in the same ring.
     *
     * @param {Vertex} vertexA A vertex.
     * @param {Vertex} vertexB A vertex.
     * @returns {Boolean} A boolean indicating whether or not the two vertices are in the same ring.
     */
    areVerticesInSameRing(vertexA, vertexB) {
      for (let i = 0; i < vertexA.value.rings.length; i++) {
        for (let j = 0; j < vertexB.value.rings.length; j++) {
          if (vertexA.value.rings[i] === vertexB.value.rings[j]) {
            return true;
          }
        }
      }
      return false;
    }
    /**
     * Returns an array of ring ids shared by both vertices.
     *
     * @param {Vertex} vertexA A vertex.
     * @param {Vertex} vertexB A vertex.
     * @returns {Number[]} An array of ids of rings shared by the two vertices.
     */
    getCommonRings(vertexA, vertexB) {
      let commonRings = [];
      for (let i = 0; i < vertexA.value.rings.length; i++) {
        for (let j = 0; j < vertexB.value.rings.length; j++) {
          if (vertexA.value.rings[i] == vertexB.value.rings[j]) {
            commonRings.push(vertexA.value.rings[i]);
          }
        }
      }
      return commonRings;
    }
    /**
     * Returns the aromatic or largest ring shared by the two vertices.
     *
     * @param {Vertex} vertexA A vertex.
     * @param {Vertex} vertexB A vertex.
     * @returns {(Ring|null)} If an aromatic common ring exists, that ring, else the largest (non-aromatic) ring, else null.
     */
    getLargestOrAromaticCommonRing(vertexA, vertexB) {
      let commonRings = this.getCommonRings(vertexA, vertexB);
      let maxSize = 0;
      let largestCommonRing = null;
      for (let i = 0; i < commonRings.length; i++) {
        let ring = this.getRing(commonRings[i]);
        let size = ring.getSize();
        if (ring.isBenzeneLike(this.graph.vertices)) {
          return ring;
        } else if (size > maxSize) {
          maxSize = size;
          largestCommonRing = ring;
        }
      }
      return largestCommonRing;
    }
    /**
     * Returns an array of vertices positioned at a specified location.
     *
     * @param {Vector2} position The position to search for vertices.
     * @param {Number} radius The radius within to search.
     * @param {Number} excludeVertexId A vertex id to be excluded from the search results.
     * @returns {Number[]} An array containing vertex ids in a given location.
     */
    getVerticesAt(position, radius, excludeVertexId) {
      let locals = [];
      for (let i = 0; i < this.graph.vertices.length; i++) {
        let vertex = this.graph.vertices[i];
        if (vertex.id === excludeVertexId || !vertex.positioned) {
          continue;
        }
        let distance = position.distanceSq(vertex.position);
        if (distance <= radius * radius) {
          locals.push(vertex.id);
        }
      }
      return locals;
    }
    /**
     * Returns the closest vertex (connected as well as unconnected).
     *
     * @param {Vertex} vertex The vertex of which to find the closest other vertex.
     * @returns {Vertex} The closest vertex.
     */
    getClosestVertex(vertex) {
      let minDist = 99999;
      let minVertex = null;
      for (let i = 0; i < this.graph.vertices.length; i++) {
        let v = this.graph.vertices[i];
        if (v.id === vertex.id) {
          continue;
        }
        let distSq = vertex.position.distanceSq(v.position);
        if (distSq < minDist) {
          minDist = distSq;
          minVertex = v;
        }
      }
      return minVertex;
    }
    /**
     * Add a ring to this representation of a molecule.
     *
     * @param {Ring} ring A new ring.
     * @returns {Number} The ring id of the new ring.
     */
    addRing(ring) {
      ring.id = this.ringIdCounter++;
      this.rings.push(ring);
      return ring.id;
    }
    /**
     * Removes a ring from the array of rings associated with the current molecule.
     *
     * @param {Number} ringId A ring id.
     */
    removeRing(ringId) {
      this.rings = this.rings.filter(function(item) {
        return item.id !== ringId;
      });
      this.ringConnections = this.ringConnections.filter(function(item) {
        return item.firstRingId !== ringId && item.secondRingId !== ringId;
      });
      for (let i = 0; i < this.rings.length; i++) {
        let r = this.rings[i];
        r.neighbours = r.neighbours.filter(function(item) {
          return item !== ringId;
        });
      }
    }
    /**
     * Gets a ring object from the array of rings associated with the current molecule by its id. The ring id is not equal to the index, since rings can be added and removed when processing bridged rings.
     *
     * @param {Number} ringId A ring id.
     * @returns {Ring} A ring associated with the current molecule.
     */
    getRing(ringId) {
      for (let i = 0; i < this.rings.length; i++) {
        if (this.rings[i].id == ringId) {
          return this.rings[i];
        }
      }
    }
    /**
     * Add a ring connection to this representation of a molecule.
     *
     * @param {RingConnection} ringConnection A new ringConnection.
     * @returns {Number} The ring connection id of the new ring connection.
     */
    addRingConnection(ringConnection) {
      ringConnection.id = this.ringConnectionIdCounter++;
      this.ringConnections.push(ringConnection);
      return ringConnection.id;
    }
    /**
     * Removes a ring connection from the array of rings connections associated with the current molecule.
     *
     * @param {Number} ringConnectionId A ring connection id.
     */
    removeRingConnection(ringConnectionId) {
      this.ringConnections = this.ringConnections.filter(function(item) {
        return item.id !== ringConnectionId;
      });
    }
    /**
     * Removes all ring connections between two vertices.
     *
     * @param {Number} vertexIdA A vertex id.
     * @param {Number} vertexIdB A vertex id.
     */
    removeRingConnectionsBetween(vertexIdA, vertexIdB) {
      let toRemove = [];
      for (let i = 0; i < this.ringConnections.length; i++) {
        let ringConnection = this.ringConnections[i];
        if (ringConnection.firstRingId === vertexIdA && ringConnection.secondRingId === vertexIdB || ringConnection.firstRingId === vertexIdB && ringConnection.secondRingId === vertexIdA) {
          toRemove.push(ringConnection.id);
        }
      }
      for (let i = 0; i < toRemove.length; i++) {
        this.removeRingConnection(toRemove[i]);
      }
    }
    /**
     * Get a ring connection with a given id.
     *
     * @param {Number} id
     * @returns {RingConnection} The ring connection with the specified id.
     */
    getRingConnection(id) {
      for (let i = 0; i < this.ringConnections.length; i++) {
        if (this.ringConnections[i].id == id) {
          return this.ringConnections[i];
        }
      }
    }
    /**
     * Get the ring connections between a ring and a set of rings.
     *
     * @param {Number} ringId A ring id.
     * @param {Number[]} ringIds An array of ring ids.
     * @returns {Number[]} An array of ring connection ids.
     */
    getRingConnections(ringId, ringIds) {
      let ringConnections = [];
      for (let i = 0; i < this.ringConnections.length; i++) {
        let rc = this.ringConnections[i];
        for (let j = 0; j < ringIds.length; j++) {
          let id = ringIds[j];
          if (rc.firstRingId === ringId && rc.secondRingId === id || rc.firstRingId === id && rc.secondRingId === ringId) {
            ringConnections.push(rc.id);
          }
        }
      }
      return ringConnections;
    }
    /**
     * Returns the overlap score of the current molecule based on its positioned vertices. The higher the score, the more overlaps occur in the structure drawing.
     *
     * @returns {Object} Returns the total overlap score and the overlap score of each vertex sorted by score (higher to lower). Example: { total: 99, scores: [ { id: 0, score: 22 }, ... ]  }
     */
    getOverlapScore() {
      let total = 0;
      let overlapScores = new Float32Array(this.graph.vertices.length);
      for (let i = 0; i < this.graph.vertices.length; i++) {
        overlapScores[i] = 0;
      }
      for (let i = 0; i < this.graph.vertices.length; i++) {
        let j = this.graph.vertices.length;
        while (--j > i) {
          let a = this.graph.vertices[i];
          let b = this.graph.vertices[j];
          if (!a.value.isDrawn || !b.value.isDrawn) {
            continue;
          }
          let dist = Vector2.subtract(a.position, b.position).lengthSq();
          if (dist < this.opts.bondLengthSq) {
            let weighted = (this.opts.bondLength - Math.sqrt(dist)) / this.opts.bondLength;
            total += weighted;
            overlapScores[i] += weighted;
            overlapScores[j] += weighted;
          }
        }
      }
      let sortable = [];
      for (let i = 0; i < this.graph.vertices.length; i++) {
        sortable.push({ id: i, score: overlapScores[i] });
      }
      sortable.sort(function(a, b) {
        return b.score - a.score;
      });
      return {
        total,
        scores: sortable,
        vertexScores: overlapScores
      };
    }
    /**
     * When drawing a double bond, choose the side to place the double bond. E.g. a double bond should always been drawn inside a ring.
     *
     * @param {Vertex} vertexA A vertex.
     * @param {Vertex} vertexB A vertex.
     * @param {Vector2[]} sides An array containing the two normals of the line spanned by the two provided vertices.
     * @returns {Object} Returns an object containing the following information: {
          totalSideCount: Counts the sides of each vertex in the molecule, is an array [ a, b ],
          totalPosition: Same as position, but based on entire molecule,
          sideCount: Counts the sides of each neighbour, is an array [ a, b ],
          position: which side to position the second bond, is 0 or 1, represents the index in the normal array. This is based on only the neighbours
          anCount: the number of neighbours of vertexA,
          bnCount: the number of neighbours of vertexB
      }
     */
    chooseSide(vertexA, vertexB, sides) {
      let an = vertexA.getNeighbours(vertexB.id);
      let bn = vertexB.getNeighbours(vertexA.id);
      let anCount = an.length;
      let bnCount = bn.length;
      let tn = ArrayHelper.merge(an, bn);
      let sideCount = [0, 0];
      for (let i = 0; i < tn.length; i++) {
        let v = this.graph.vertices[tn[i]].position;
        if (v.sameSideAs(vertexA.position, vertexB.position, sides[0])) {
          sideCount[0]++;
        } else {
          sideCount[1]++;
        }
      }
      let totalSideCount = [0, 0];
      for (let i = 0; i < this.graph.vertices.length; i++) {
        let v = this.graph.vertices[i].position;
        if (v.sameSideAs(vertexA.position, vertexB.position, sides[0])) {
          totalSideCount[0]++;
        } else {
          totalSideCount[1]++;
        }
      }
      return {
        totalSideCount,
        totalPosition: totalSideCount[0] > totalSideCount[1] ? 0 : 1,
        sideCount,
        position: sideCount[0] > sideCount[1] ? 0 : 1,
        anCount,
        bnCount
      };
    }
    /**
     * Sets the center for a ring.
     *
     * @param {Ring} ring A ring.
     */
    setRingCenter(ring) {
      let ringSize = ring.getSize();
      let total = new Vector2(0, 0);
      for (let i = 0; i < ringSize; i++) {
        total.add(this.graph.vertices[ring.members[i]].position);
      }
      ring.center = total.divide(ringSize);
    }
    /**
     * Gets the center of a ring contained within a bridged ring and containing a given vertex.
     *
     * @param {Ring} ring A bridged ring.
     * @param {Vertex} vertex A vertex.
     * @returns {Vector2} The center of the subring that containing the vertex.
     */
    getSubringCenter(ring, vertex) {
      let rings = vertex.value.originalRings;
      let center = ring.center;
      let smallest = Number.MAX_VALUE;
      for (let i = 0; i < rings.length; i++) {
        for (let j = 0; j < ring.rings.length; j++) {
          if (rings[i] === ring.rings[j].id) {
            if (ring.rings[j].getSize() < smallest) {
              center = ring.rings[j].center;
              smallest = ring.rings[j].getSize();
            }
          }
        }
      }
      return center;
    }
    /**
     * Draw the actual edges as bonds to the canvas.
     *
     * @param {Boolean} debug A boolean indicating whether or not to draw debug helpers.
     */
    drawEdges(debug) {
      let drawn = Array(this.graph.edges.length);
      drawn.fill(false);
      this.graph.traverseBF(0, (vertex) => {
        let edges = this.graph.getEdges(vertex.id);
        for (let i = 0; i < edges.length; i++) {
          let edgeId = edges[i];
          if (!drawn[edgeId]) {
            drawn[edgeId] = true;
            this.drawEdge(edgeId, debug);
          }
        }
      });
      if (!this.bridgedRing) {
        for (let i = 0; i < this.rings.length; i++) {
          let ring = this.rings[i];
          if (this.isRingAromatic(ring)) {
            this.canvasWrapper.drawAromaticityRing(ring);
          }
        }
      }
    }
    /**
     * Draw the an edge as a bonds to the canvas.
     *
     * @param {Number} edgeId An edge id.
     * @param {Boolean} debug A boolean indicating whether or not to draw debug helpers.
     */
    drawEdge(edgeId, debug) {
      let edge = this.graph.edges[edgeId];
      let vertexA = this.graph.vertices[edge.sourceId];
      let vertexB = this.graph.vertices[edge.targetId];
      let elementA = vertexA.value.element;
      let elementB = vertexB.value.element;
      if ((!vertexA.value.isDrawn || !vertexB.value.isDrawn) && this.opts.atomVisualization === "default") {
        return;
      }
      let a = vertexA.position;
      let b = vertexB.position;
      let normals = this.getEdgeNormals(edge);
      let sides = ArrayHelper.clone(normals);
      sides[0].multiplyScalar(10).add(a);
      sides[1].multiplyScalar(10).add(a);
      if (edge.bondType === "=" || this.getRingbondType(vertexA, vertexB) === "=" || edge.isPartOfAromaticRing && this.bridgedRing) {
        let inRing = this.areVerticesInSameRing(vertexA, vertexB);
        let s = this.chooseSide(vertexA, vertexB, sides);
        if (inRing) {
          let lcr = this.getLargestOrAromaticCommonRing(vertexA, vertexB);
          let center = lcr.center;
          normals[0].multiplyScalar(this.opts.bondSpacing);
          normals[1].multiplyScalar(this.opts.bondSpacing);
          let line = null;
          if (center.sameSideAs(vertexA.position, vertexB.position, Vector2.add(a, normals[0]))) {
            line = new Line(Vector2.add(a, normals[0]), Vector2.add(b, normals[0]), elementA, elementB);
          } else {
            line = new Line(Vector2.add(a, normals[1]), Vector2.add(b, normals[1]), elementA, elementB);
          }
          line.shorten(this.opts.bondLength - this.opts.shortBondLength * this.opts.bondLength);
          if (edge.isPartOfAromaticRing) {
            this.canvasWrapper.drawLine(line, true);
          } else {
            this.canvasWrapper.drawLine(line);
          }
          this.canvasWrapper.drawLine(new Line(a, b, elementA, elementB));
        } else if (edge.center || vertexA.isTerminal() && vertexB.isTerminal()) {
          normals[0].multiplyScalar(this.opts.halfBondSpacing);
          normals[1].multiplyScalar(this.opts.halfBondSpacing);
          let lineA = new Line(Vector2.add(a, normals[0]), Vector2.add(b, normals[0]), elementA, elementB);
          let lineB = new Line(Vector2.add(a, normals[1]), Vector2.add(b, normals[1]), elementA, elementB);
          this.canvasWrapper.drawLine(lineA);
          this.canvasWrapper.drawLine(lineB);
        } else if (s.anCount == 0 && s.bnCount > 1 || s.bnCount == 0 && s.anCount > 1) {
          normals[0].multiplyScalar(this.opts.halfBondSpacing);
          normals[1].multiplyScalar(this.opts.halfBondSpacing);
          let lineA = new Line(Vector2.add(a, normals[0]), Vector2.add(b, normals[0]), elementA, elementB);
          let lineB = new Line(Vector2.add(a, normals[1]), Vector2.add(b, normals[1]), elementA, elementB);
          this.canvasWrapper.drawLine(lineA);
          this.canvasWrapper.drawLine(lineB);
        } else if (s.sideCount[0] > s.sideCount[1]) {
          normals[0].multiplyScalar(this.opts.bondSpacing);
          normals[1].multiplyScalar(this.opts.bondSpacing);
          let line = new Line(Vector2.add(a, normals[0]), Vector2.add(b, normals[0]), elementA, elementB);
          line.shorten(this.opts.bondLength - this.opts.shortBondLength * this.opts.bondLength);
          this.canvasWrapper.drawLine(line);
          this.canvasWrapper.drawLine(new Line(a, b, elementA, elementB));
        } else if (s.sideCount[0] < s.sideCount[1]) {
          normals[0].multiplyScalar(this.opts.bondSpacing);
          normals[1].multiplyScalar(this.opts.bondSpacing);
          let line = new Line(Vector2.add(a, normals[1]), Vector2.add(b, normals[1]), elementA, elementB);
          line.shorten(this.opts.bondLength - this.opts.shortBondLength * this.opts.bondLength);
          this.canvasWrapper.drawLine(line);
          this.canvasWrapper.drawLine(new Line(a, b, elementA, elementB));
        } else if (s.totalSideCount[0] > s.totalSideCount[1]) {
          normals[0].multiplyScalar(this.opts.bondSpacing);
          normals[1].multiplyScalar(this.opts.bondSpacing);
          let line = new Line(Vector2.add(a, normals[0]), Vector2.add(b, normals[0]), elementA, elementB);
          line.shorten(this.opts.bondLength - this.opts.shortBondLength * this.opts.bondLength);
          this.canvasWrapper.drawLine(line);
          this.canvasWrapper.drawLine(new Line(a, b, elementA, elementB));
        } else if (s.totalSideCount[0] <= s.totalSideCount[1]) {
          normals[0].multiplyScalar(this.opts.bondSpacing);
          normals[1].multiplyScalar(this.opts.bondSpacing);
          let line = new Line(Vector2.add(a, normals[1]), Vector2.add(b, normals[1]), elementA, elementB);
          line.shorten(this.opts.bondLength - this.opts.shortBondLength * this.opts.bondLength);
          this.canvasWrapper.drawLine(line);
          this.canvasWrapper.drawLine(new Line(a, b, elementA, elementB));
        }
      } else if (edge.bondType === "#") {
        normals[0].multiplyScalar(this.opts.bondSpacing / 1.5);
        normals[1].multiplyScalar(this.opts.bondSpacing / 1.5);
        let lineA = new Line(Vector2.add(a, normals[0]), Vector2.add(b, normals[0]), elementA, elementB);
        let lineB = new Line(Vector2.add(a, normals[1]), Vector2.add(b, normals[1]), elementA, elementB);
        this.canvasWrapper.drawLine(lineA);
        this.canvasWrapper.drawLine(lineB);
        this.canvasWrapper.drawLine(new Line(a, b, elementA, elementB));
      } else if (edge.bondType === ".") {
      } else {
        let isChiralCenterA = vertexA.value.isStereoCenter;
        let isChiralCenterB = vertexB.value.isStereoCenter;
        if (edge.wedge === "up") {
          this.canvasWrapper.drawWedge(new Line(a, b, elementA, elementB, isChiralCenterA, isChiralCenterB));
        } else if (edge.wedge === "down") {
          this.canvasWrapper.drawDashedWedge(new Line(a, b, elementA, elementB, isChiralCenterA, isChiralCenterB));
        } else {
          this.canvasWrapper.drawLine(new Line(a, b, elementA, elementB, isChiralCenterA, isChiralCenterB));
        }
      }
      if (debug) {
        let midpoint = Vector2.midpoint(a, b);
        this.canvasWrapper.drawDebugText(midpoint.x, midpoint.y, "e: " + edgeId);
      }
    }
    /**
     * Draws the vertices representing atoms to the canvas.
     *
     * @param {Boolean} debug A boolean indicating whether or not to draw debug messages to the canvas.
     */
    drawVertices(debug) {
      for (let i = 0; i < this.graph.vertices.length; i++) {
        let vertex = this.graph.vertices[i];
        let atom = vertex.value;
        let charge = 0;
        let isotope = 0;
        let bondCount = vertex.value.bondCount;
        let element = atom.element;
        let hydrogens = Atom.maxBonds[element] - bondCount;
        let dir = vertex.getTextDirection(this.graph.vertices);
        let isTerminal = this.opts.terminalCarbons || element !== "C" || atom.hasAttachedPseudoElements ? vertex.isTerminal() : false;
        let isCarbon = atom.element === "C";
        if (atom.element === "N" && atom.isPartOfAromaticRing) {
          hydrogens = 0;
        }
        if (atom.bracket) {
          hydrogens = atom.bracket.hcount;
          charge = atom.bracket.charge;
          isotope = atom.bracket.isotope;
        }
        if (charge || isotope || this.graph.vertices.length < 3) {
          isCarbon = false;
        }
        if (this.opts.atomVisualization === "allballs") {
          this.canvasWrapper.drawBall(vertex.position.x, vertex.position.y, element);
        } else if (atom.isDrawn && (!isCarbon || atom.drawExplicit || isTerminal || atom.hasAttachedPseudoElements) || this.graph.vertices.length === 1) {
          if (this.opts.atomVisualization === "default") {
            this.canvasWrapper.drawText(
              vertex.position.x,
              vertex.position.y,
              element,
              hydrogens,
              dir,
              isTerminal,
              charge,
              isotope,
              this.graph.vertices.length,
              atom.getAttachedPseudoElements()
            );
          } else if (this.opts.atomVisualization === "balls") {
            this.canvasWrapper.drawBall(vertex.position.x, vertex.position.y, element);
          }
        } else if (vertex.getNeighbourCount() === 2 && vertex.forcePositioned == true) {
          let a = this.graph.vertices[vertex.neighbours[0]].position;
          let b = this.graph.vertices[vertex.neighbours[1]].position;
          let angle = Vector2.threePointangle(vertex.position, a, b);
          if (Math.abs(Math.PI - angle) < 0.1) {
            this.canvasWrapper.drawPoint(vertex.position.x, vertex.position.y, element);
          }
        }
        if (debug) {
          let value = "v: " + vertex.id + " " + ArrayHelper.print(atom.ringbonds);
          this.canvasWrapper.drawDebugText(vertex.position.x, vertex.position.y, value);
        } else {
        }
      }
      if (this.opts.debug) {
        for (let i = 0; i < this.rings.length; i++) {
          let center = this.rings[i].center;
          this.canvasWrapper.drawDebugPoint(center.x, center.y, "r: " + this.rings[i].id);
        }
      }
    }
    /**
     * Position the vertices according to their bonds and properties.
     */
    position() {
      let startVertex = null;
      for (let i = 0; i < this.graph.vertices.length; i++) {
        if (this.graph.vertices[i].value.bridgedRing !== null) {
          startVertex = this.graph.vertices[i];
          break;
        }
      }
      for (let i = 0; i < this.rings.length; i++) {
        if (this.rings[i].isBridged) {
          startVertex = this.graph.vertices[this.rings[i].members[0]];
        }
      }
      if (this.rings.length > 0 && startVertex === null) {
        startVertex = this.graph.vertices[this.rings[0].members[0]];
      }
      if (startVertex === null) {
        startVertex = this.graph.vertices[0];
      }
      this.createNextBond(startVertex, null, 0);
    }
    /**
     * Stores the current information associated with rings.
     */
    backupRingInformation() {
      this.originalRings = [];
      this.originalRingConnections = [];
      for (let i = 0; i < this.rings.length; i++) {
        this.originalRings.push(this.rings[i]);
      }
      for (let i = 0; i < this.ringConnections.length; i++) {
        this.originalRingConnections.push(this.ringConnections[i]);
      }
      for (let i = 0; i < this.graph.vertices.length; i++) {
        this.graph.vertices[i].value.backupRings();
      }
    }
    /**
     * Restores the most recently backed up information associated with rings.
     */
    restoreRingInformation() {
      let bridgedRings = this.getBridgedRings();
      this.rings = [];
      this.ringConnections = [];
      for (let i = 0; i < bridgedRings.length; i++) {
        let bridgedRing = bridgedRings[i];
        for (let j = 0; j < bridgedRing.rings.length; j++) {
          let ring = bridgedRing.rings[j];
          this.originalRings[ring.id].center = ring.center;
        }
      }
      for (let i = 0; i < this.originalRings.length; i++) {
        this.rings.push(this.originalRings[i]);
      }
      for (let i = 0; i < this.originalRingConnections.length; i++) {
        this.ringConnections.push(this.originalRingConnections[i]);
      }
      for (let i = 0; i < this.graph.vertices.length; i++) {
        this.graph.vertices[i].value.restoreRings();
      }
    }
    // TODO: This needs some cleaning up
    /**
     * Creates a new ring, that is, positiones all the vertices inside a ring.
     *
     * @param {Ring} ring The ring to position.
     * @param {(Vector2|null)} [center=null] The center of the ring to be created.
     * @param {(Vertex|null)} [startVertex=null] The first vertex to be positioned inside the ring.
     * @param {(Vertex|null)} [previousVertex=null] The last vertex that was positioned.
     * @param {Boolean} [previousVertex=false] A boolean indicating whether or not this ring was force positioned already - this is needed after force layouting a ring, in order to draw rings connected to it.
     */
    createRing(ring, center = null, startVertex = null, previousVertex = null) {
      if (ring.positioned) {
        return;
      }
      center = center ? center : new Vector2(0, 0);
      let orderedNeighbours = ring.getOrderedNeighbours(this.ringConnections);
      let startingAngle = startVertex ? Vector2.subtract(startVertex.position, center).angle() : 0;
      let radius = MathHelper.polyCircumradius(this.opts.bondLength, ring.getSize());
      let angle = MathHelper.centralAngle(ring.getSize());
      ring.centralAngle = angle;
      let a = startingAngle;
      let startVertexId = startVertex ? startVertex.id : null;
      if (ring.members.indexOf(startVertexId) === -1) {
        if (startVertex) {
          startVertex.positioned = false;
        }
        startVertexId = ring.members[0];
      }
      if (ring.isBridged) {
        this.graph.kkLayout(
          ring.members.slice(),
          center,
          startVertex.id,
          ring,
          this.opts.bondLength,
          this.opts.kkThreshold,
          this.opts.kkInnerThreshold,
          this.opts.kkMaxIteration,
          this.opts.kkMaxInnerIteration,
          this.opts.kkMaxEnergy
        );
        ring.positioned = true;
        this.setRingCenter(ring);
        center = ring.center;
        for (let i = 0; i < ring.rings.length; i++) {
          this.setRingCenter(ring.rings[i]);
        }
      } else {
        ring.eachMember(this.graph.vertices, (v) => {
          let vertex = this.graph.vertices[v];
          if (!vertex.positioned) {
            vertex.setPosition(center.x + Math.cos(a) * radius, center.y + Math.sin(a) * radius);
          }
          a += angle;
          if (!ring.isBridged || ring.rings.length < 3) {
            vertex.angle = a;
            vertex.positioned = true;
          }
        }, startVertexId, previousVertex ? previousVertex.id : null);
      }
      ring.positioned = true;
      ring.center = center;
      for (let i = 0; i < orderedNeighbours.length; i++) {
        let neighbour = this.getRing(orderedNeighbours[i].neighbour);
        if (neighbour.positioned) {
          continue;
        }
        let vertices = RingConnection.getVertices(this.ringConnections, ring.id, neighbour.id);
        if (vertices.length === 2) {
          ring.isFused = true;
          neighbour.isFused = true;
          let vertexA = this.graph.vertices[vertices[0]];
          let vertexB = this.graph.vertices[vertices[1]];
          let midpoint = Vector2.midpoint(vertexA.position, vertexB.position);
          let normals = Vector2.normals(vertexA.position, vertexB.position);
          normals[0].normalize();
          normals[1].normalize();
          let r = MathHelper.polyCircumradius(this.opts.bondLength, neighbour.getSize());
          let apothem = MathHelper.apothem(r, neighbour.getSize());
          normals[0].multiplyScalar(apothem).add(midpoint);
          normals[1].multiplyScalar(apothem).add(midpoint);
          let nextCenter = normals[0];
          if (Vector2.subtract(center, normals[1]).lengthSq() > Vector2.subtract(center, normals[0]).lengthSq()) {
            nextCenter = normals[1];
          }
          let posA = Vector2.subtract(vertexA.position, nextCenter);
          let posB = Vector2.subtract(vertexB.position, nextCenter);
          if (posA.clockwise(posB) === -1) {
            if (!neighbour.positioned) {
              this.createRing(neighbour, nextCenter, vertexA, vertexB);
            }
          } else {
            if (!neighbour.positioned) {
              this.createRing(neighbour, nextCenter, vertexB, vertexA);
            }
          }
        } else if (vertices.length === 1) {
          ring.isSpiro = true;
          neighbour.isSpiro = true;
          let vertexA = this.graph.vertices[vertices[0]];
          let nextCenter = Vector2.subtract(center, vertexA.position);
          nextCenter.invert();
          nextCenter.normalize();
          let r = MathHelper.polyCircumradius(this.opts.bondLength, neighbour.getSize());
          nextCenter.multiplyScalar(r);
          nextCenter.add(vertexA.position);
          if (!neighbour.positioned) {
            this.createRing(neighbour, nextCenter, vertexA);
          }
        }
      }
      for (let i = 0; i < ring.members.length; i++) {
        let ringMember = this.graph.vertices[ring.members[i]];
        let ringMemberNeighbours = ringMember.neighbours;
        for (let j = 0; j < ringMemberNeighbours.length; j++) {
          let v = this.graph.vertices[ringMemberNeighbours[j]];
          if (v.positioned) {
            continue;
          }
          v.value.isConnectedToRing = true;
          this.createNextBond(v, ringMember, 0);
        }
      }
    }
    /**
     * Rotate an entire subtree by an angle around a center.
     *
     * @param {Number} vertexId A vertex id (the root of the sub-tree).
     * @param {Number} parentVertexId A vertex id in the previous direction of the subtree that is to rotate.
     * @param {Number} angle An angle in randians.
     * @param {Vector2} center The rotational center.
     */
    rotateSubtree(vertexId, parentVertexId, angle, center) {
      this.graph.traverseTree(vertexId, parentVertexId, (vertex) => {
        vertex.position.rotateAround(angle, center);
        for (let i = 0; i < vertex.value.anchoredRings.length; i++) {
          let ring = this.rings[vertex.value.anchoredRings[i]];
          if (ring) {
            ring.center.rotateAround(angle, center);
          }
        }
      });
    }
    /**
     * Gets the overlap score of a subtree.
     *
     * @param {Number} vertexId A vertex id (the root of the sub-tree).
     * @param {Number} parentVertexId A vertex id in the previous direction of the subtree.
     * @param {Number[]} vertexOverlapScores An array containing the vertex overlap scores indexed by vertex id.
     * @returns {Object} An object containing the total overlap score and the center of mass of the subtree weighted by overlap score { value: 0.2, center: new Vector2() }.
     */
    getSubtreeOverlapScore(vertexId, parentVertexId, vertexOverlapScores) {
      let score = 0;
      let center = new Vector2(0, 0);
      let count = 0;
      this.graph.traverseTree(vertexId, parentVertexId, (vertex) => {
        if (!vertex.value.isDrawn) {
          return;
        }
        let s = vertexOverlapScores[vertex.id];
        if (s > this.opts.overlapSensitivity) {
          score += s;
          count++;
        }
        let position = this.graph.vertices[vertex.id].position.clone();
        position.multiplyScalar(s);
        center.add(position);
      });
      center.divide(score);
      return {
        value: score / count,
        center
      };
    }
    /**
     * Returns the current (positioned vertices so far) center of mass.
     *
     * @returns {Vector2} The current center of mass.
     */
    getCurrentCenterOfMass() {
      let total = new Vector2(0, 0);
      let count = 0;
      for (let i = 0; i < this.graph.vertices.length; i++) {
        let vertex = this.graph.vertices[i];
        if (vertex.positioned) {
          total.add(vertex.position);
          count++;
        }
      }
      return total.divide(count);
    }
    /**
     * Returns the current (positioned vertices so far) center of mass in the neighbourhood of a given position.
     *
     * @param {Vector2} vec The point at which to look for neighbours.
     * @param {Number} [r=currentBondLength*2.0] The radius of vertices to include.
     * @returns {Vector2} The current center of mass.
     */
    getCurrentCenterOfMassInNeigbourhood(vec, r = this.opts.bondLength * 2) {
      let total = new Vector2(0, 0);
      let count = 0;
      let rSq = r * r;
      for (let i = 0; i < this.graph.vertices.length; i++) {
        let vertex = this.graph.vertices[i];
        if (vertex.positioned && vec.distanceSq(vertex.position) < rSq) {
          total.add(vertex.position);
          count++;
        }
      }
      return total.divide(count);
    }
    /**
     * Resolve primary (exact) overlaps, such as two vertices that are connected to the same ring vertex.
     */
    resolvePrimaryOverlaps() {
      let overlaps = [];
      let done = Array(this.graph.vertices.length);
      for (let i = 0; i < this.rings.length; i++) {
        let ring = this.rings[i];
        for (let j = 0; j < ring.members.length; j++) {
          let vertex = this.graph.vertices[ring.members[j]];
          if (done[vertex.id]) {
            continue;
          }
          done[vertex.id] = true;
          let nonRingNeighbours = this.getNonRingNeighbours(vertex.id);
          if (nonRingNeighbours.length > 1) {
            let rings = [];
            for (let k = 0; k < vertex.value.rings.length; k++) {
              rings.push(vertex.value.rings[k]);
            }
            overlaps.push({
              common: vertex,
              rings,
              vertices: nonRingNeighbours
            });
          } else if (nonRingNeighbours.length === 1 && vertex.value.rings.length === 2) {
            let rings = [];
            for (let k = 0; k < vertex.value.rings.length; k++) {
              rings.push(vertex.value.rings[k]);
            }
            overlaps.push({
              common: vertex,
              rings,
              vertices: nonRingNeighbours
            });
          }
        }
      }
      for (let i = 0; i < overlaps.length; i++) {
        let overlap = overlaps[i];
        if (overlap.vertices.length === 2) {
          let a = overlap.vertices[0];
          let b = overlap.vertices[1];
          if (!a.value.isDrawn || !b.value.isDrawn) {
            continue;
          }
          let angle = (2 * Math.PI - this.getRing(overlap.rings[0]).getAngle()) / 6;
          this.rotateSubtree(a.id, overlap.common.id, angle, overlap.common.position);
          this.rotateSubtree(b.id, overlap.common.id, -angle, overlap.common.position);
          let overlapScore = this.getOverlapScore();
          let subTreeOverlapA = this.getSubtreeOverlapScore(a.id, overlap.common.id, overlapScore.vertexScores);
          let subTreeOverlapB = this.getSubtreeOverlapScore(b.id, overlap.common.id, overlapScore.vertexScores);
          let total = subTreeOverlapA.value + subTreeOverlapB.value;
          this.rotateSubtree(a.id, overlap.common.id, -2 * angle, overlap.common.position);
          this.rotateSubtree(b.id, overlap.common.id, 2 * angle, overlap.common.position);
          overlapScore = this.getOverlapScore();
          subTreeOverlapA = this.getSubtreeOverlapScore(a.id, overlap.common.id, overlapScore.vertexScores);
          subTreeOverlapB = this.getSubtreeOverlapScore(b.id, overlap.common.id, overlapScore.vertexScores);
          if (subTreeOverlapA.value + subTreeOverlapB.value > total) {
            this.rotateSubtree(a.id, overlap.common.id, 2 * angle, overlap.common.position);
            this.rotateSubtree(b.id, overlap.common.id, -2 * angle, overlap.common.position);
          }
        } else if (overlap.vertices.length === 1) {
          if (overlap.rings.length === 2) {
          }
        }
      }
    }
    /**
     * Resolve secondary overlaps. Those overlaps are due to the structure turning back on itself.
     *
     * @param {Object[]} scores An array of objects sorted descending by score.
     * @param {Number} scores[].id A vertex id.
     * @param {Number} scores[].score The overlap score associated with the vertex id.
     */
    resolveSecondaryOverlaps(scores) {
      for (let i = 0; i < scores.length; i++) {
        if (scores[i].score > this.opts.overlapSensitivity) {
          let vertex = this.graph.vertices[scores[i].id];
          if (vertex.isTerminal()) {
            let closest = this.getClosestVertex(vertex);
            if (closest) {
              let closestPosition = null;
              if (closest.isTerminal()) {
                closestPosition = closest.id === 0 ? this.graph.vertices[1].position : closest.previousPosition;
              } else {
                closestPosition = closest.id === 0 ? this.graph.vertices[1].position : closest.position;
              }
              let vertexPreviousPosition = vertex.id === 0 ? this.graph.vertices[1].position : vertex.previousPosition;
              vertex.position.rotateAwayFrom(closestPosition, vertexPreviousPosition, MathHelper.toRad(20));
            }
          }
        }
      }
    }
    /**
     * Get the last non-null or 0 angle.
     * @param {Number} vertexId A vertex id.
     * @returns {Number} The last angle that was not 0 or null.
     */
    getLastAngle(vertexId) {
      while (vertexId) {
        let vertex = this.graph.vertices[vertexId];
        if (vertex.value.rings.length > 0) {
          return 0;
        }
        if (vertex.angle) {
          return vertex.angle;
        }
        vertexId = vertex.parentVertexId;
      }
      return 0;
    }
    /**
     * Positiones the next vertex thus creating a bond.
     *
     * @param {Vertex} vertex A vertex.
     * @param {Vertex} [previousVertex=null] The previous vertex which has been positioned.
     * @param {Number} [angle=0.0] The (global) angle of the vertex.
     * @param {Boolean} [originShortest=false] Whether the origin is the shortest subtree in the branch.
     * @param {Boolean} [skipPositioning=false] Whether or not to skip positioning and just check the neighbours.
     */
    createNextBond(vertex, previousVertex = null, angle = 0, originShortest = false, skipPositioning = false) {
      if (vertex.positioned && !skipPositioning) {
        return;
      }
      let doubleBondConfigSet = false;
      if (previousVertex) {
        let edge = this.graph.getEdge(vertex.id, previousVertex.id);
        if ((edge.bondType === "/" || edge.bondType === "\\") && ++this.doubleBondConfigCount % 2 === 1) {
          if (this.doubleBondConfig === null) {
            this.doubleBondConfig = edge.bondType;
            doubleBondConfigSet = true;
            if (previousVertex.parentVertexId === null && vertex.value.branchBond) {
              if (this.doubleBondConfig === "/") {
                this.doubleBondConfig = "\\";
              } else if (this.doubleBondConfig === "\\") {
                this.doubleBondConfig = "/";
              }
            }
          }
        }
      }
      if (!skipPositioning) {
        if (!previousVertex) {
          let dummy = new Vector2(this.opts.bondLength, 0);
          dummy.rotate(MathHelper.toRad(-60));
          vertex.previousPosition = dummy;
          vertex.setPosition(this.opts.bondLength, 0);
          vertex.angle = MathHelper.toRad(-60);
          if (vertex.value.bridgedRing === null) {
            vertex.positioned = true;
          }
        } else if (previousVertex.value.rings.length > 0) {
          let neighbours = previousVertex.neighbours;
          let joinedVertex = null;
          let pos = new Vector2(0, 0);
          if (previousVertex.value.bridgedRing === null && previousVertex.value.rings.length > 1) {
            for (let i = 0; i < neighbours.length; i++) {
              let neighbour = this.graph.vertices[neighbours[i]];
              if (ArrayHelper.containsAll(neighbour.value.rings, previousVertex.value.rings)) {
                joinedVertex = neighbour;
                break;
              }
            }
          }
          if (joinedVertex === null) {
            for (let i = 0; i < neighbours.length; i++) {
              let v = this.graph.vertices[neighbours[i]];
              if (v.positioned && this.areVerticesInSameRing(v, previousVertex)) {
                pos.add(Vector2.subtract(v.position, previousVertex.position));
              }
            }
            if (pos.lengthSq() < 1) {
              let ring = null;
              if (previousVertex.value.bridgedRing !== null) {
                ring = this.getRing(previousVertex.value.bridgedRing);
              } else {
                ring = this.getRing(previousVertex.value.rings[0]);
              }
              if (ring && ring.center) {
                pos = Vector2.subtract(ring.center, previousVertex.position);
              } else {
                pos = new Vector2(1, 0);
              }
            }
            pos.invert().normalize().multiplyScalar(this.opts.bondLength).add(previousVertex.position);
          } else {
            pos = joinedVertex.position.clone().rotateAround(Math.PI, previousVertex.position);
          }
          vertex.previousPosition = previousVertex.position;
          vertex.setPositionFromVector(pos);
          vertex.positioned = true;
        } else {
          let v = new Vector2(this.opts.bondLength, 0);
          v.rotate(angle);
          v.add(previousVertex.position);
          vertex.setPositionFromVector(v);
          vertex.previousPosition = previousVertex.position;
          vertex.positioned = true;
        }
      }
      if (vertex.value.bridgedRing !== null) {
        let nextRing = this.getRing(vertex.value.bridgedRing);
        if (!nextRing.positioned) {
          let nextCenter = Vector2.subtract(vertex.previousPosition, vertex.position);
          nextCenter.invert();
          nextCenter.normalize();
          let r = MathHelper.polyCircumradius(this.opts.bondLength, nextRing.members.length);
          nextCenter.multiplyScalar(r);
          nextCenter.add(vertex.position);
          this.createRing(nextRing, nextCenter, vertex);
        }
      } else if (vertex.value.rings.length > 0) {
        let nextRing = this.getRing(vertex.value.rings[0]);
        if (!nextRing.positioned) {
          let nextCenter = Vector2.subtract(vertex.previousPosition, vertex.position);
          nextCenter.invert();
          nextCenter.normalize();
          let r = MathHelper.polyCircumradius(this.opts.bondLength, nextRing.getSize());
          nextCenter.multiplyScalar(r);
          nextCenter.add(vertex.position);
          this.createRing(nextRing, nextCenter, vertex);
        }
      } else {
        let tmpNeighbours = vertex.getNeighbours();
        let neighbours = [];
        for (let i = 0; i < tmpNeighbours.length; i++) {
          if (this.graph.vertices[tmpNeighbours[i]].value.isDrawn) {
            neighbours.push(tmpNeighbours[i]);
          }
        }
        if (previousVertex) {
          neighbours = ArrayHelper.remove(neighbours, previousVertex.id);
        }
        let previousAngle = vertex.getAngle();
        if (neighbours.length === 1) {
          let nextVertex = this.graph.vertices[neighbours[0]];
          let prevEdge = previousVertex ? this.graph.getEdge(vertex.id, previousVertex.id) : null;
          let nextEdge = this.graph.getEdge(vertex.id, nextVertex.id);
          if (prevEdge && nextEdge && prevEdge.weight + nextEdge.weight >= 4) {
            prevEdge.center = true;
            nextEdge.center = true;
            vertex.value.drawExplicit = false;
            nextVertex.drawExplicit = true;
            nextVertex.angle = 0;
            this.createNextBond(nextVertex, vertex, previousAngle + nextVertex.angle);
          } else if (previousVertex && previousVertex.value.rings.length > 0) {
            let proposedAngleA = MathHelper.toRad(60);
            let proposedAngleB = -proposedAngleA;
            let proposedVectorA = new Vector2(this.opts.bondLength, 0);
            let proposedVectorB = new Vector2(this.opts.bondLength, 0);
            proposedVectorA.rotate(proposedAngleA).add(vertex.position);
            proposedVectorB.rotate(proposedAngleB).add(vertex.position);
            let centerOfMass = this.getCurrentCenterOfMass();
            let distanceA = proposedVectorA.distanceSq(centerOfMass);
            let distanceB = proposedVectorB.distanceSq(centerOfMass);
            nextVertex.angle = distanceA < distanceB ? proposedAngleB : proposedAngleA;
            this.createNextBond(nextVertex, vertex, previousAngle + nextVertex.angle);
          } else {
            let a = this.getLastAngle(vertex.id);
            a = a >= 0 ? 1.0472 : -1.0472;
            if (previousVertex && !doubleBondConfigSet) {
              let bondType = this.graph.getEdge(vertex.id, nextVertex.id).bondType;
              if (bondType === "/") {
                if (this.doubleBondConfig === "/") {
                } else if (this.doubleBondConfig === "\\") {
                  a = -a;
                }
                this.doubleBondConfig = null;
              } else if (bondType === "\\") {
                if (this.doubleBondConfig === "/") {
                  a = -a;
                } else if (this.doubleBondConfig === "\\") {
                }
                this.doubleBondConfig = null;
              }
            }
            if (originShortest) {
              nextVertex.angle = a;
            } else {
              nextVertex.angle = -a;
            }
            this.createNextBond(nextVertex, vertex, previousAngle + nextVertex.angle);
          }
        } else if (neighbours.length === 2) {
          let a = vertex.angle;
          if (!a) {
            a = 1.0472;
          }
          let subTreeDepthA = this.graph.getTreeDepth(neighbours[0], vertex.id);
          let subTreeDepthB = this.graph.getTreeDepth(neighbours[1], vertex.id);
          let l = this.graph.vertices[neighbours[0]];
          let r = this.graph.vertices[neighbours[1]];
          l.value.subtreeDepth = subTreeDepthA;
          r.value.subtreeDepth = subTreeDepthB;
          let subTreeDepthC = this.graph.getTreeDepth(previousVertex ? previousVertex.id : null, vertex.id);
          if (previousVertex) {
            previousVertex.value.subtreeDepth = subTreeDepthC;
          }
          let cis = 0;
          let trans = 1;
          if (r.value.element === "C" && l.value.element !== "C" && subTreeDepthB > 1 && subTreeDepthA < 5) {
            cis = 1;
            trans = 0;
          } else if (r.value.element !== "C" && l.value.element === "C" && subTreeDepthA > 1 && subTreeDepthB < 5) {
            cis = 0;
            trans = 1;
          } else if (subTreeDepthB > subTreeDepthA) {
            cis = 1;
            trans = 0;
          }
          let cisVertex = this.graph.vertices[neighbours[cis]];
          let transVertex = this.graph.vertices[neighbours[trans]];
          let prevShortest = subTreeDepthC < subTreeDepthA && subTreeDepthC < subTreeDepthB;
          transVertex.angle = a;
          cisVertex.angle = -a;
          if (this.doubleBondConfig === "\\") {
            if (transVertex.value.branchBond === "\\") {
              transVertex.angle = -a;
              cisVertex.angle = a;
            }
          } else if (this.doubleBondConfig === "/") {
            if (transVertex.value.branchBond === "/") {
              transVertex.angle = -a;
              cisVertex.angle = a;
            }
          }
          this.createNextBond(transVertex, vertex, previousAngle + transVertex.angle, prevShortest);
          this.createNextBond(cisVertex, vertex, previousAngle + cisVertex.angle, prevShortest);
        } else if (neighbours.length > 0) {
          const vertices = neighbours.map((neighbour) => {
            let newvertex = this.graph.vertices[neighbour];
            let subtreedepth = this.graph.getTreeDepth(neighbour, vertex.id);
            newvertex.value.subtreeDepth = subtreedepth;
            return newvertex;
          });
          vertices.sort((a, b) => b.value.subtreeDepth - a.value.subtreeDepth);
          if (neighbours.length === 3 && previousVertex && previousVertex.parentVertexId !== null && previousVertex.value.rings.length < 1 && vertices[2].value.rings.length < 1 && vertices[1].value.rings.length < 1 && vertices[0].value.rings.length < 1 && vertices[2].value.subtreeDepth === 1 && vertices[1].value.subtreeDepth === 1 && vertices[0].value.subtreeDepth > 1) {
            if (vertex.angle >= 0) {
              vertices[0].angle = -1.0472;
              vertices[1].angle = MathHelper.toRad(30);
              vertices[2].angle = MathHelper.toRad(90);
            } else {
              vertices[0].angle = 1.0472;
              vertices[1].angle = -MathHelper.toRad(30);
              vertices[2].angle = -MathHelper.toRad(90);
            }
            this.createNextBond(vertices[0], vertex, previousAngle + vertices[0].angle);
            this.createNextBond(vertices[1], vertex, previousAngle + vertices[1].angle);
            this.createNextBond(vertices[2], vertex, previousAngle + vertices[2].angle);
          } else {
            const totalNeighbors = neighbours.length + (previousVertex ? 1 : 0);
            const angleDelta = 2 * Math.PI / totalNeighbors;
            let a = angleDelta;
            let i = 0;
            if (neighbours.length % 2 !== 0) {
              this.createNextBond(vertices[0], vertex, previousAngle);
              i = 1;
            } else {
              a /= 2;
            }
            while (i < neighbours.length) {
              this.createNextBond(vertices[i + 0], vertex, previousAngle + a);
              this.createNextBond(vertices[i + 1], vertex, previousAngle - a);
              a += angleDelta;
              i += 2;
            }
          }
        }
      }
    }
    /**
     * Gets the vetex sharing the edge that is the common bond of two rings.
     *
     * @param {Vertex} vertex A vertex.
     * @returns {(Number|null)} The id of a vertex sharing the edge that is the common bond of two rings with the vertex provided or null, if none.
     */
    getCommonRingbondNeighbour(vertex) {
      let neighbours = vertex.neighbours;
      for (let i = 0; i < neighbours.length; i++) {
        let neighbour = this.graph.vertices[neighbours[i]];
        if (ArrayHelper.containsAll(neighbour.value.rings, vertex.value.rings)) {
          return neighbour;
        }
      }
      return null;
    }
    /**
     * Check if a vector is inside any ring.
     *
     * @param {Vector2} vec A vector.
     * @returns {Boolean} A boolean indicating whether or not the point (vector) is inside any of the rings associated with the current molecule.
     */
    isPointInRing(vec) {
      for (let i = 0; i < this.rings.length; i++) {
        let ring = this.rings[i];
        if (!ring.positioned) {
          continue;
        }
        let radius = MathHelper.polyCircumradius(this.opts.bondLength, ring.getSize());
        let radiusSq = radius * radius;
        if (vec.distanceSq(ring.center) < radiusSq) {
          return true;
        }
      }
      return false;
    }
    /**
     * Check whether or not an edge is part of a ring.
     *
     * @param {Edge} edge An edge.
     * @returns {Boolean} A boolean indicating whether or not the edge is part of a ring.
     */
    isEdgeInRing(edge) {
      let source = this.graph.vertices[edge.sourceId];
      let target = this.graph.vertices[edge.targetId];
      return this.areVerticesInSameRing(source, target);
    }
    /**
     * Check whether or not an edge is rotatable.
     *
     * @param {Edge} edge An edge.
     * @returns {Boolean} A boolean indicating whether or not the edge is rotatable.
     */
    isEdgeRotatable(edge) {
      let vertexA = this.graph.vertices[edge.sourceId];
      let vertexB = this.graph.vertices[edge.targetId];
      if (edge.bondType !== "-") {
        return false;
      }
      if (vertexA.isTerminal() || vertexB.isTerminal()) {
        return false;
      }
      if (vertexA.value.rings.length > 0 && vertexB.value.rings.length > 0 && this.areVerticesInSameRing(vertexA, vertexB)) {
        return false;
      }
      return true;
    }
    /**
     * Check whether or not a ring is an implicitly defined aromatic ring (lower case smiles).
     *
     * @param {Ring} ring A ring.
     * @returns {Boolean} A boolean indicating whether or not a ring is implicitly defined as aromatic.
     */
    isRingAromatic(ring) {
      for (let i = 0; i < ring.members.length; i++) {
        let vertex = this.graph.vertices[ring.members[i]];
        if (!vertex.value.isPartOfAromaticRing) {
          return false;
        }
      }
      return true;
    }
    /**
     * Get the normals of an edge.
     *
     * @param {Edge} edge An edge.
     * @returns {Vector2[]} An array containing two vectors, representing the normals.
     */
    getEdgeNormals(edge) {
      let v1 = this.graph.vertices[edge.sourceId].position;
      let v2 = this.graph.vertices[edge.targetId].position;
      let normals = Vector2.units(v1, v2);
      return normals;
    }
    /**
     * Returns an array of vertices that are neighbouring a vertix but are not members of a ring (including bridges).
     *
     * @param {Number} vertexId A vertex id.
     * @returns {Vertex[]} An array of vertices.
     */
    getNonRingNeighbours(vertexId) {
      let nrneighbours = [];
      let vertex = this.graph.vertices[vertexId];
      let neighbours = vertex.neighbours;
      for (let i = 0; i < neighbours.length; i++) {
        let neighbour = this.graph.vertices[neighbours[i]];
        let nIntersections = ArrayHelper.intersection(vertex.value.rings, neighbour.value.rings).length;
        if (nIntersections === 0 && neighbour.value.isBridge == false) {
          nrneighbours.push(neighbour);
        }
      }
      return nrneighbours;
    }
    /**
     * Annotaed stereochemistry information for visualization.
     */
    annotateStereochemistry() {
      let maxDepth = 10;
      for (let i = 0; i < this.graph.vertices.length; i++) {
        let vertex = this.graph.vertices[i];
        if (!vertex.value.isStereoCenter) {
          continue;
        }
        let neighbours = vertex.getNeighbours();
        let nNeighbours = neighbours.length;
        let priorities = Array(nNeighbours);
        for (let j = 0; j < nNeighbours; j++) {
          let visited = new Uint8Array(this.graph.vertices.length);
          let priority = Array([]);
          visited[vertex.id] = 1;
          this.visitStereochemistry(neighbours[j], vertex.id, visited, priority, maxDepth, 0);
          for (let k = 0; k < priority.length; k++) {
            priority[k].sort((a, b) => b - a);
          }
          priorities[j] = [j, priority];
        }
        let maxLevels = 0;
        let maxEntries = 0;
        for (let j = 0; j < priorities.length; j++) {
          if (priorities[j][1].length > maxLevels) {
            maxLevels = priorities[j][1].length;
          }
          for (let k = 0; k < priorities[j][1].length; k++) {
            if (priorities[j][1][k].length > maxEntries) {
              maxEntries = priorities[j][1][k].length;
            }
          }
        }
        for (let j = 0; j < priorities.length; j++) {
          let kmax = maxLevels - priorities[j][1].length;
          for (let k = 0; k < kmax; k++) {
            priorities[j][1].push([]);
          }
          priorities[j][1].push([neighbours[j]]);
          for (let k = 0; k < priorities[j][1].length; k++) {
            let lmax = maxEntries - priorities[j][1][k].length;
            for (let l = 0; l < lmax; l++) {
              priorities[j][1][k].push(0);
            }
          }
        }
        priorities.sort(function(a, b) {
          for (let j = 0; j < a[1].length; j++) {
            for (let k = 0; k < a[1][j].length; k++) {
              if (a[1][j][k] > b[1][j][k]) {
                return -1;
              } else if (a[1][j][k] < b[1][j][k]) {
                return 1;
              }
            }
          }
          return 0;
        });
        let order = new Uint8Array(nNeighbours);
        for (let j = 0; j < nNeighbours; j++) {
          order[j] = priorities[j][0];
          vertex.value.priority = j;
        }
        let posA = this.graph.vertices[neighbours[order[0]]].position;
        let posB = this.graph.vertices[neighbours[order[1]]].position;
        let cwA = posA.relativeClockwise(posB, vertex.position);
        let isCw = cwA === -1;
        let rotation = vertex.value.bracket.chirality === "@" ? -1 : 1;
        let rs = MathHelper.parityOfPermutation(order) * rotation === 1 ? "R" : "S";
        let wedgeA = "down";
        let wedgeB = "up";
        if (isCw && rs !== "R" || !isCw && rs !== "S") {
          vertex.value.hydrogenDirection = "up";
          wedgeA = "up";
          wedgeB = "down";
        }
        if (vertex.value.hasHydrogen) {
          this.graph.getEdge(vertex.id, neighbours[order[order.length - 1]]).wedge = wedgeA;
        }
        let wedgeOrder = new Array(neighbours.length - 1);
        let showHydrogen = vertex.value.rings.length > 1 && vertex.value.hasHydrogen;
        let offset = vertex.value.hasHydrogen ? 1 : 0;
        for (let j = 0; j < order.length - offset; j++) {
          wedgeOrder[j] = new Uint32Array(2);
          let neighbour = this.graph.vertices[neighbours[order[j]]];
          wedgeOrder[j][0] += neighbour.value.isStereoCenter ? 0 : 1e5;
          wedgeOrder[j][0] += this.areVerticesInSameRing(neighbour, vertex) ? 0 : 1e4;
          wedgeOrder[j][0] += neighbour.value.isHeteroAtom() ? 1e3 : 0;
          wedgeOrder[j][0] -= neighbour.value.subtreeDepth === 0 ? 1e3 : 0;
          wedgeOrder[j][0] += 1e3 - neighbour.value.subtreeDepth;
          wedgeOrder[j][1] = neighbours[order[j]];
        }
        wedgeOrder.sort(function(a, b) {
          if (a[0] > b[0]) {
            return -1;
          } else if (a[0] < b[0]) {
            return 1;
          }
          return 0;
        });
        if (!showHydrogen) {
          let wedgeId = wedgeOrder[0][1];
          if (vertex.value.hasHydrogen) {
            this.graph.getEdge(vertex.id, wedgeId).wedge = wedgeB;
          } else {
            let wedge = wedgeB;
            for (let j = order.length - 1; j >= 0; j--) {
              if (wedge === wedgeA) {
                wedge = wedgeB;
              } else {
                wedge = wedgeA;
              }
              if (neighbours[order[j]] === wedgeId) {
                break;
              }
            }
            this.graph.getEdge(vertex.id, wedgeId).wedge = wedge;
          }
        }
        vertex.value.chirality = rs;
      }
    }
    /**
     *
     *
     * @param {Number} vertexId The id of a vertex.
     * @param {(Number|null)} previousVertexId The id of the parent vertex of the vertex.
     * @param {Uint8Array} visited An array containing the visited flag for all vertices in the graph.
     * @param {Array} priority An array of arrays storing the atomic numbers for each level.
     * @param {Number} maxDepth The maximum depth.
     * @param {Number} depth The current depth.
     */
    visitStereochemistry(vertexId, previousVertexId, visited, priority, maxDepth, depth, parentAtomicNumber = 0) {
      visited[vertexId] = 1;
      let vertex = this.graph.vertices[vertexId];
      let atomicNumber = vertex.value.getAtomicNumber();
      if (priority.length <= depth) {
        priority.push([]);
      }
      for (let i = 0; i < this.graph.getEdge(vertexId, previousVertexId).weight; i++) {
        priority[depth].push(parentAtomicNumber * 1e3 + atomicNumber);
      }
      let neighbours = this.graph.vertices[vertexId].neighbours;
      for (let i = 0; i < neighbours.length; i++) {
        if (visited[neighbours[i]] !== 1 && depth < maxDepth - 1) {
          this.visitStereochemistry(neighbours[i], vertexId, visited.slice(), priority, maxDepth, depth + 1, atomicNumber);
        }
      }
      if (depth < maxDepth - 1) {
        let bonds = 0;
        for (let i = 0; i < neighbours.length; i++) {
          bonds += this.graph.getEdge(vertexId, neighbours[i]).weight;
        }
        for (let i = 0; i < vertex.value.getMaxBonds() - bonds; i++) {
          if (priority.length <= depth + 1) {
            priority.push([]);
          }
          priority[depth + 1].push(atomicNumber * 1e3 + 1);
        }
      }
    }
    /**
     * Creates pseudo-elements (such as Et, Me, Ac, Bz, ...) at the position of the carbon sets
     * the involved atoms not to be displayed.
     */
    initPseudoElements() {
      for (let i = 0; i < this.graph.vertices.length; i++) {
        const vertex = this.graph.vertices[i];
        const neighbourIds = vertex.neighbours;
        let neighbours = Array(neighbourIds.length);
        for (let j = 0; j < neighbourIds.length; j++) {
          neighbours[j] = this.graph.vertices[neighbourIds[j]];
        }
        if (vertex.getNeighbourCount() < 3 || vertex.value.rings.length > 0) {
          continue;
        }
        if (vertex.value.element === "P") {
          continue;
        }
        if (vertex.value.element === "C" && neighbours.length === 3 && neighbours[0].value.element === "N" && neighbours[1].value.element === "N" && neighbours[2].value.element === "N") {
          continue;
        }
        let heteroAtomCount = 0;
        let ctn = 0;
        for (let j = 0; j < neighbours.length; j++) {
          let neighbour = neighbours[j];
          let neighbouringElement = neighbour.value.element;
          let neighbourCount = neighbour.getNeighbourCount();
          if (neighbouringElement !== "C" && neighbouringElement !== "H" && neighbourCount === 1) {
            heteroAtomCount++;
          }
          if (neighbourCount > 1) {
            ctn++;
          }
        }
        if (ctn > 1 || heteroAtomCount < 2) {
          continue;
        }
        let previous = null;
        for (let j = 0; j < neighbours.length; j++) {
          let neighbour = neighbours[j];
          if (neighbour.getNeighbourCount() > 1) {
            previous = neighbour;
          }
        }
        for (let j = 0; j < neighbours.length; j++) {
          let neighbour = neighbours[j];
          if (neighbour.getNeighbourCount() > 1) {
            continue;
          }
          neighbour.value.isDrawn = false;
          let hydrogens = Atom.maxBonds[neighbour.value.element] - neighbour.value.bondCount;
          let charge = "";
          if (neighbour.value.bracket) {
            hydrogens = neighbour.value.bracket.hcount;
            charge = neighbour.value.bracket.charge || 0;
          }
          vertex.value.attachPseudoElement(neighbour.value.element, previous ? previous.value.element : null, hydrogens, charge);
        }
      }
    }
  };

  // node_modules/smiles-drawer/src/PixelsToSvg.js
  function convertImage(img) {
    "use strict";
    function each2(obj, fn) {
      let length = obj.length, likeArray = length === 0 || length > 0 && length - 1 in obj;
      if (likeArray) {
        for (let i = 0; i < length; i++) {
          if (fn.call(obj[i], i, obj[i]) === false) {
            break;
          }
        }
      } else {
        for (const i in obj) {
          if (fn.call(obj[i], i, obj[i]) === false) {
            break;
          }
        }
      }
    }
    function componentToHex(c) {
      let hex = parseInt(c).toString(16);
      return hex.length == 1 ? "0" + hex : hex;
    }
    function getColor(r, g, b, a) {
      a = parseInt(a);
      if (a === void 0 || a === 255) {
        return "#" + componentToHex(r) + componentToHex(g) + componentToHex(b);
      }
      if (a === 0) {
        return false;
      }
      return "rgba(" + r + "," + g + "," + b + "," + a / 255 + ")";
    }
    function makePathData(x, y, w) {
      return "M" + x + " " + y + "h" + w;
    }
    function makePath(color, data) {
      return '<path stroke="' + color + '" d="' + data + '" />\n';
    }
    function colorsToPaths(colors2) {
      let output2 = "";
      each2(colors2, function(color, values) {
        color = getColor.apply(null, color.split(","));
        if (color === false) {
          return;
        }
        let paths2 = [];
        let curPath;
        let w = 1;
        each2(values, function(index, value) {
          if (curPath && value[1] === curPath[1] && value[0] === curPath[0] + w) {
            w++;
          } else {
            if (curPath) {
              paths2.push(makePathData(curPath[0], curPath[1], w));
              w = 1;
            }
            curPath = value;
          }
        });
        paths2.push(makePathData(curPath[0], curPath[1], w));
        output2 += makePath(color, paths2.join(""));
      });
      return output2;
    }
    function getColors(image) {
      let colors2 = {}, data = image.data, len = data.length, w = image.width, x = 0, y = 0, color;
      for (let i = 0; i < len; i += 4) {
        if (data[i + 3] > 0) {
          color = data[i] + "," + data[i + 1] + "," + data[i + 2] + "," + data[i + 3];
          colors2[color] = colors2[color] || [];
          x = i / 4 % w;
          y = Math.floor(i / 4 / w);
          colors2[color].push([x, y]);
        }
      }
      return colors2;
    }
    let colors = getColors(img);
    let paths = colorsToPaths(colors);
    let output = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 -0.5 ' + img.width + " " + img.height + '" shape-rendering="crispEdges"><g shape-rendering="crispEdges">' + paths + "</g></svg>";
    let dummyDiv = document.createElement("div");
    dummyDiv.innerHTML = output;
    return dummyDiv.firstChild;
  }

  // node_modules/chroma-js/src/utils/limit.js
  var limit_default = (x, low = 0, high = 1) => {
    return min(max(low, x), high);
  };

  // node_modules/chroma-js/src/utils/clip_rgb.js
  var clip_rgb_default = (rgb2) => {
    rgb2._clipped = false;
    rgb2._unclipped = rgb2.slice(0);
    for (let i = 0; i <= 3; i++) {
      if (i < 3) {
        if (rgb2[i] < 0 || rgb2[i] > 255) rgb2._clipped = true;
        rgb2[i] = limit_default(rgb2[i], 0, 255);
      } else if (i === 3) {
        rgb2[i] = limit_default(rgb2[i], 0, 1);
      }
    }
    return rgb2;
  };

  // node_modules/chroma-js/src/utils/type.js
  var classToType = {};
  for (let name of [
    "Boolean",
    "Number",
    "String",
    "Function",
    "Array",
    "Date",
    "RegExp",
    "Undefined",
    "Null"
  ]) {
    classToType[`[object ${name}]`] = name.toLowerCase();
  }
  function type_default(obj) {
    return classToType[Object.prototype.toString.call(obj)] || "object";
  }

  // node_modules/chroma-js/src/utils/unpack.js
  var unpack_default = (args, keyOrder = null) => {
    if (args.length >= 3) return Array.prototype.slice.call(args);
    if (type_default(args[0]) == "object" && keyOrder) {
      return keyOrder.split("").filter((k) => args[0][k] !== void 0).map((k) => args[0][k]);
    }
    return args[0];
  };

  // node_modules/chroma-js/src/utils/last.js
  var last_default = (args) => {
    if (args.length < 2) return null;
    const l = args.length - 1;
    if (type_default(args[l]) == "string") return args[l].toLowerCase();
    return null;
  };

  // node_modules/chroma-js/src/utils/index.js
  var { PI, min, max } = Math;
  var TWOPI = PI * 2;
  var PITHIRD = PI / 3;
  var DEG2RAD = PI / 180;
  var RAD2DEG = 180 / PI;

  // node_modules/chroma-js/src/io/input.js
  var input_default = {
    format: {},
    autodetect: []
  };

  // node_modules/chroma-js/src/Color.js
  var Color = class {
    constructor(...args) {
      const me = this;
      if (type_default(args[0]) === "object" && args[0].constructor && args[0].constructor === this.constructor) {
        return args[0];
      }
      let mode = last_default(args);
      let autodetect = false;
      if (!mode) {
        autodetect = true;
        if (!input_default.sorted) {
          input_default.autodetect = input_default.autodetect.sort((a, b) => b.p - a.p);
          input_default.sorted = true;
        }
        for (let chk of input_default.autodetect) {
          mode = chk.test(...args);
          if (mode) break;
        }
      }
      if (input_default.format[mode]) {
        const rgb2 = input_default.format[mode].apply(
          null,
          autodetect ? args : args.slice(0, -1)
        );
        me._rgb = clip_rgb_default(rgb2);
      } else {
        throw new Error("unknown format: " + args);
      }
      if (me._rgb.length === 3) me._rgb.push(1);
    }
    toString() {
      if (type_default(this.hex) == "function") return this.hex();
      return `[${this._rgb.join(",")}]`;
    }
  };
  var Color_default = Color;

  // node_modules/chroma-js/src/version.js
  var version = "2.6.0";

  // node_modules/chroma-js/src/chroma.js
  var chroma = (...args) => {
    return new chroma.Color(...args);
  };
  chroma.Color = Color_default;
  chroma.version = version;
  var chroma_default = chroma;

  // node_modules/chroma-js/src/io/cmyk/cmyk2rgb.js
  var cmyk2rgb = (...args) => {
    args = unpack_default(args, "cmyk");
    const [c, m, y, k] = args;
    const alpha = args.length > 4 ? args[4] : 1;
    if (k === 1) return [0, 0, 0, alpha];
    return [
      c >= 1 ? 0 : 255 * (1 - c) * (1 - k),
      // r
      m >= 1 ? 0 : 255 * (1 - m) * (1 - k),
      // g
      y >= 1 ? 0 : 255 * (1 - y) * (1 - k),
      // b
      alpha
    ];
  };
  var cmyk2rgb_default = cmyk2rgb;

  // node_modules/chroma-js/src/io/cmyk/rgb2cmyk.js
  var { max: max2 } = Math;
  var rgb2cmyk = (...args) => {
    let [r, g, b] = unpack_default(args, "rgb");
    r = r / 255;
    g = g / 255;
    b = b / 255;
    const k = 1 - max2(r, max2(g, b));
    const f = k < 1 ? 1 / (1 - k) : 0;
    const c = (1 - r - k) * f;
    const m = (1 - g - k) * f;
    const y = (1 - b - k) * f;
    return [c, m, y, k];
  };
  var rgb2cmyk_default = rgb2cmyk;

  // node_modules/chroma-js/src/io/cmyk/index.js
  Color_default.prototype.cmyk = function() {
    return rgb2cmyk_default(this._rgb);
  };
  chroma_default.cmyk = (...args) => new Color_default(...args, "cmyk");
  input_default.format.cmyk = cmyk2rgb_default;
  input_default.autodetect.push({
    p: 2,
    test: (...args) => {
      args = unpack_default(args, "cmyk");
      if (type_default(args) === "array" && args.length === 4) {
        return "cmyk";
      }
    }
  });

  // node_modules/chroma-js/src/io/css/hsl2css.js
  var rnd = (a) => Math.round(a * 100) / 100;
  var hsl2css = (...args) => {
    const hsla = unpack_default(args, "hsla");
    let mode = last_default(args) || "lsa";
    hsla[0] = rnd(hsla[0] || 0);
    hsla[1] = rnd(hsla[1] * 100) + "%";
    hsla[2] = rnd(hsla[2] * 100) + "%";
    if (mode === "hsla" || hsla.length > 3 && hsla[3] < 1) {
      hsla[3] = hsla.length > 3 ? hsla[3] : 1;
      mode = "hsla";
    } else {
      hsla.length = 3;
    }
    return `${mode}(${hsla.join(",")})`;
  };
  var hsl2css_default = hsl2css;

  // node_modules/chroma-js/src/io/hsl/rgb2hsl.js
  var rgb2hsl = (...args) => {
    args = unpack_default(args, "rgba");
    let [r, g, b] = args;
    r /= 255;
    g /= 255;
    b /= 255;
    const minRgb = min(r, g, b);
    const maxRgb = max(r, g, b);
    const l = (maxRgb + minRgb) / 2;
    let s, h;
    if (maxRgb === minRgb) {
      s = 0;
      h = Number.NaN;
    } else {
      s = l < 0.5 ? (maxRgb - minRgb) / (maxRgb + minRgb) : (maxRgb - minRgb) / (2 - maxRgb - minRgb);
    }
    if (r == maxRgb) h = (g - b) / (maxRgb - minRgb);
    else if (g == maxRgb) h = 2 + (b - r) / (maxRgb - minRgb);
    else if (b == maxRgb) h = 4 + (r - g) / (maxRgb - minRgb);
    h *= 60;
    if (h < 0) h += 360;
    if (args.length > 3 && args[3] !== void 0) return [h, s, l, args[3]];
    return [h, s, l];
  };
  var rgb2hsl_default = rgb2hsl;

  // node_modules/chroma-js/src/io/css/rgb2css.js
  var { round } = Math;
  var rgb2css = (...args) => {
    const rgba = unpack_default(args, "rgba");
    let mode = last_default(args) || "rgb";
    if (mode.substr(0, 3) == "hsl") {
      return hsl2css_default(rgb2hsl_default(rgba), mode);
    }
    rgba[0] = round(rgba[0]);
    rgba[1] = round(rgba[1]);
    rgba[2] = round(rgba[2]);
    if (mode === "rgba" || rgba.length > 3 && rgba[3] < 1) {
      rgba[3] = rgba.length > 3 ? rgba[3] : 1;
      mode = "rgba";
    }
    return `${mode}(${rgba.slice(0, mode === "rgb" ? 3 : 4).join(",")})`;
  };
  var rgb2css_default = rgb2css;

  // node_modules/chroma-js/src/io/hsl/hsl2rgb.js
  var { round: round2 } = Math;
  var hsl2rgb = (...args) => {
    args = unpack_default(args, "hsl");
    const [h, s, l] = args;
    let r, g, b;
    if (s === 0) {
      r = g = b = l * 255;
    } else {
      const t3 = [0, 0, 0];
      const c = [0, 0, 0];
      const t2 = l < 0.5 ? l * (1 + s) : l + s - l * s;
      const t1 = 2 * l - t2;
      const h_ = h / 360;
      t3[0] = h_ + 1 / 3;
      t3[1] = h_;
      t3[2] = h_ - 1 / 3;
      for (let i = 0; i < 3; i++) {
        if (t3[i] < 0) t3[i] += 1;
        if (t3[i] > 1) t3[i] -= 1;
        if (6 * t3[i] < 1) c[i] = t1 + (t2 - t1) * 6 * t3[i];
        else if (2 * t3[i] < 1) c[i] = t2;
        else if (3 * t3[i] < 2) c[i] = t1 + (t2 - t1) * (2 / 3 - t3[i]) * 6;
        else c[i] = t1;
      }
      [r, g, b] = [round2(c[0] * 255), round2(c[1] * 255), round2(c[2] * 255)];
    }
    if (args.length > 3) {
      return [r, g, b, args[3]];
    }
    return [r, g, b, 1];
  };
  var hsl2rgb_default = hsl2rgb;

  // node_modules/chroma-js/src/io/css/css2rgb.js
  var RE_RGB = /^rgb\(\s*(-?\d+),\s*(-?\d+)\s*,\s*(-?\d+)\s*\)$/;
  var RE_RGBA = /^rgba\(\s*(-?\d+),\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*([01]|[01]?\.\d+)\)$/;
  var RE_RGB_PCT = /^rgb\(\s*(-?\d+(?:\.\d+)?)%,\s*(-?\d+(?:\.\d+)?)%\s*,\s*(-?\d+(?:\.\d+)?)%\s*\)$/;
  var RE_RGBA_PCT = /^rgba\(\s*(-?\d+(?:\.\d+)?)%,\s*(-?\d+(?:\.\d+)?)%\s*,\s*(-?\d+(?:\.\d+)?)%\s*,\s*([01]|[01]?\.\d+)\)$/;
  var RE_HSL = /^hsl\(\s*(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)%\s*,\s*(-?\d+(?:\.\d+)?)%\s*\)$/;
  var RE_HSLA = /^hsla\(\s*(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)%\s*,\s*(-?\d+(?:\.\d+)?)%\s*,\s*([01]|[01]?\.\d+)\)$/;
  var { round: round3 } = Math;
  var css2rgb = (css) => {
    css = css.toLowerCase().trim();
    let m;
    if (input_default.format.named) {
      try {
        return input_default.format.named(css);
      } catch (e) {
      }
    }
    if (m = css.match(RE_RGB)) {
      const rgb2 = m.slice(1, 4);
      for (let i = 0; i < 3; i++) {
        rgb2[i] = +rgb2[i];
      }
      rgb2[3] = 1;
      return rgb2;
    }
    if (m = css.match(RE_RGBA)) {
      const rgb2 = m.slice(1, 5);
      for (let i = 0; i < 4; i++) {
        rgb2[i] = +rgb2[i];
      }
      return rgb2;
    }
    if (m = css.match(RE_RGB_PCT)) {
      const rgb2 = m.slice(1, 4);
      for (let i = 0; i < 3; i++) {
        rgb2[i] = round3(rgb2[i] * 2.55);
      }
      rgb2[3] = 1;
      return rgb2;
    }
    if (m = css.match(RE_RGBA_PCT)) {
      const rgb2 = m.slice(1, 5);
      for (let i = 0; i < 3; i++) {
        rgb2[i] = round3(rgb2[i] * 2.55);
      }
      rgb2[3] = +rgb2[3];
      return rgb2;
    }
    if (m = css.match(RE_HSL)) {
      const hsl2 = m.slice(1, 4);
      hsl2[1] *= 0.01;
      hsl2[2] *= 0.01;
      const rgb2 = hsl2rgb_default(hsl2);
      rgb2[3] = 1;
      return rgb2;
    }
    if (m = css.match(RE_HSLA)) {
      const hsl2 = m.slice(1, 4);
      hsl2[1] *= 0.01;
      hsl2[2] *= 0.01;
      const rgb2 = hsl2rgb_default(hsl2);
      rgb2[3] = +m[4];
      return rgb2;
    }
  };
  css2rgb.test = (s) => {
    return RE_RGB.test(s) || RE_RGBA.test(s) || RE_RGB_PCT.test(s) || RE_RGBA_PCT.test(s) || RE_HSL.test(s) || RE_HSLA.test(s);
  };
  var css2rgb_default = css2rgb;

  // node_modules/chroma-js/src/io/css/index.js
  Color_default.prototype.css = function(mode) {
    return rgb2css_default(this._rgb, mode);
  };
  chroma_default.css = (...args) => new Color_default(...args, "css");
  input_default.format.css = css2rgb_default;
  input_default.autodetect.push({
    p: 5,
    test: (h, ...rest) => {
      if (!rest.length && type_default(h) === "string" && css2rgb_default.test(h)) {
        return "css";
      }
    }
  });

  // node_modules/chroma-js/src/io/gl/index.js
  input_default.format.gl = (...args) => {
    const rgb2 = unpack_default(args, "rgba");
    rgb2[0] *= 255;
    rgb2[1] *= 255;
    rgb2[2] *= 255;
    return rgb2;
  };
  chroma_default.gl = (...args) => new Color_default(...args, "gl");
  Color_default.prototype.gl = function() {
    const rgb2 = this._rgb;
    return [rgb2[0] / 255, rgb2[1] / 255, rgb2[2] / 255, rgb2[3]];
  };

  // node_modules/chroma-js/src/io/hcg/hcg2rgb.js
  var { floor } = Math;
  var hcg2rgb = (...args) => {
    args = unpack_default(args, "hcg");
    let [h, c, _g] = args;
    let r, g, b;
    _g = _g * 255;
    const _c = c * 255;
    if (c === 0) {
      r = g = b = _g;
    } else {
      if (h === 360) h = 0;
      if (h > 360) h -= 360;
      if (h < 0) h += 360;
      h /= 60;
      const i = floor(h);
      const f = h - i;
      const p = _g * (1 - c);
      const q = p + _c * (1 - f);
      const t = p + _c * f;
      const v = p + _c;
      switch (i) {
        case 0:
          [r, g, b] = [v, t, p];
          break;
        case 1:
          [r, g, b] = [q, v, p];
          break;
        case 2:
          [r, g, b] = [p, v, t];
          break;
        case 3:
          [r, g, b] = [p, q, v];
          break;
        case 4:
          [r, g, b] = [t, p, v];
          break;
        case 5:
          [r, g, b] = [v, p, q];
          break;
      }
    }
    return [r, g, b, args.length > 3 ? args[3] : 1];
  };
  var hcg2rgb_default = hcg2rgb;

  // node_modules/chroma-js/src/io/hcg/rgb2hcg.js
  var rgb2hcg = (...args) => {
    const [r, g, b] = unpack_default(args, "rgb");
    const minRgb = min(r, g, b);
    const maxRgb = max(r, g, b);
    const delta = maxRgb - minRgb;
    const c = delta * 100 / 255;
    const _g = minRgb / (255 - delta) * 100;
    let h;
    if (delta === 0) {
      h = Number.NaN;
    } else {
      if (r === maxRgb) h = (g - b) / delta;
      if (g === maxRgb) h = 2 + (b - r) / delta;
      if (b === maxRgb) h = 4 + (r - g) / delta;
      h *= 60;
      if (h < 0) h += 360;
    }
    return [h, c, _g];
  };
  var rgb2hcg_default = rgb2hcg;

  // node_modules/chroma-js/src/io/hcg/index.js
  Color_default.prototype.hcg = function() {
    return rgb2hcg_default(this._rgb);
  };
  chroma_default.hcg = (...args) => new Color_default(...args, "hcg");
  input_default.format.hcg = hcg2rgb_default;
  input_default.autodetect.push({
    p: 1,
    test: (...args) => {
      args = unpack_default(args, "hcg");
      if (type_default(args) === "array" && args.length === 3) {
        return "hcg";
      }
    }
  });

  // node_modules/chroma-js/src/io/hex/hex2rgb.js
  var RE_HEX = /^#?([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/;
  var RE_HEXA = /^#?([A-Fa-f0-9]{8}|[A-Fa-f0-9]{4})$/;
  var hex2rgb = (hex) => {
    if (hex.match(RE_HEX)) {
      if (hex.length === 4 || hex.length === 7) {
        hex = hex.substr(1);
      }
      if (hex.length === 3) {
        hex = hex.split("");
        hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
      }
      const u = parseInt(hex, 16);
      const r = u >> 16;
      const g = u >> 8 & 255;
      const b = u & 255;
      return [r, g, b, 1];
    }
    if (hex.match(RE_HEXA)) {
      if (hex.length === 5 || hex.length === 9) {
        hex = hex.substr(1);
      }
      if (hex.length === 4) {
        hex = hex.split("");
        hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2] + hex[3] + hex[3];
      }
      const u = parseInt(hex, 16);
      const r = u >> 24 & 255;
      const g = u >> 16 & 255;
      const b = u >> 8 & 255;
      const a = Math.round((u & 255) / 255 * 100) / 100;
      return [r, g, b, a];
    }
    throw new Error(`unknown hex color: ${hex}`);
  };
  var hex2rgb_default = hex2rgb;

  // node_modules/chroma-js/src/io/hex/rgb2hex.js
  var { round: round4 } = Math;
  var rgb2hex = (...args) => {
    let [r, g, b, a] = unpack_default(args, "rgba");
    let mode = last_default(args) || "auto";
    if (a === void 0) a = 1;
    if (mode === "auto") {
      mode = a < 1 ? "rgba" : "rgb";
    }
    r = round4(r);
    g = round4(g);
    b = round4(b);
    const u = r << 16 | g << 8 | b;
    let str = "000000" + u.toString(16);
    str = str.substr(str.length - 6);
    let hxa = "0" + round4(a * 255).toString(16);
    hxa = hxa.substr(hxa.length - 2);
    switch (mode.toLowerCase()) {
      case "rgba":
        return `#${str}${hxa}`;
      case "argb":
        return `#${hxa}${str}`;
      default:
        return `#${str}`;
    }
  };
  var rgb2hex_default = rgb2hex;

  // node_modules/chroma-js/src/io/hex/index.js
  Color_default.prototype.hex = function(mode) {
    return rgb2hex_default(this._rgb, mode);
  };
  chroma_default.hex = (...args) => new Color_default(...args, "hex");
  input_default.format.hex = hex2rgb_default;
  input_default.autodetect.push({
    p: 4,
    test: (h, ...rest) => {
      if (!rest.length && type_default(h) === "string" && [3, 4, 5, 6, 7, 8, 9].indexOf(h.length) >= 0) {
        return "hex";
      }
    }
  });

  // node_modules/chroma-js/src/io/hsi/hsi2rgb.js
  var { cos } = Math;
  var hsi2rgb = (...args) => {
    args = unpack_default(args, "hsi");
    let [h, s, i] = args;
    let r, g, b;
    if (isNaN(h)) h = 0;
    if (isNaN(s)) s = 0;
    if (h > 360) h -= 360;
    if (h < 0) h += 360;
    h /= 360;
    if (h < 1 / 3) {
      b = (1 - s) / 3;
      r = (1 + s * cos(TWOPI * h) / cos(PITHIRD - TWOPI * h)) / 3;
      g = 1 - (b + r);
    } else if (h < 2 / 3) {
      h -= 1 / 3;
      r = (1 - s) / 3;
      g = (1 + s * cos(TWOPI * h) / cos(PITHIRD - TWOPI * h)) / 3;
      b = 1 - (r + g);
    } else {
      h -= 2 / 3;
      g = (1 - s) / 3;
      b = (1 + s * cos(TWOPI * h) / cos(PITHIRD - TWOPI * h)) / 3;
      r = 1 - (g + b);
    }
    r = limit_default(i * r * 3);
    g = limit_default(i * g * 3);
    b = limit_default(i * b * 3);
    return [r * 255, g * 255, b * 255, args.length > 3 ? args[3] : 1];
  };
  var hsi2rgb_default = hsi2rgb;

  // node_modules/chroma-js/src/io/hsi/rgb2hsi.js
  var { min: min2, sqrt, acos } = Math;
  var rgb2hsi = (...args) => {
    let [r, g, b] = unpack_default(args, "rgb");
    r /= 255;
    g /= 255;
    b /= 255;
    let h;
    const min_ = min2(r, g, b);
    const i = (r + g + b) / 3;
    const s = i > 0 ? 1 - min_ / i : 0;
    if (s === 0) {
      h = NaN;
    } else {
      h = (r - g + (r - b)) / 2;
      h /= sqrt((r - g) * (r - g) + (r - b) * (g - b));
      h = acos(h);
      if (b > g) {
        h = TWOPI - h;
      }
      h /= TWOPI;
    }
    return [h * 360, s, i];
  };
  var rgb2hsi_default = rgb2hsi;

  // node_modules/chroma-js/src/io/hsi/index.js
  Color_default.prototype.hsi = function() {
    return rgb2hsi_default(this._rgb);
  };
  chroma_default.hsi = (...args) => new Color_default(...args, "hsi");
  input_default.format.hsi = hsi2rgb_default;
  input_default.autodetect.push({
    p: 2,
    test: (...args) => {
      args = unpack_default(args, "hsi");
      if (type_default(args) === "array" && args.length === 3) {
        return "hsi";
      }
    }
  });

  // node_modules/chroma-js/src/io/hsl/index.js
  Color_default.prototype.hsl = function() {
    return rgb2hsl_default(this._rgb);
  };
  chroma_default.hsl = (...args) => new Color_default(...args, "hsl");
  input_default.format.hsl = hsl2rgb_default;
  input_default.autodetect.push({
    p: 2,
    test: (...args) => {
      args = unpack_default(args, "hsl");
      if (type_default(args) === "array" && args.length === 3) {
        return "hsl";
      }
    }
  });

  // node_modules/chroma-js/src/io/hsv/hsv2rgb.js
  var { floor: floor2 } = Math;
  var hsv2rgb = (...args) => {
    args = unpack_default(args, "hsv");
    let [h, s, v] = args;
    let r, g, b;
    v *= 255;
    if (s === 0) {
      r = g = b = v;
    } else {
      if (h === 360) h = 0;
      if (h > 360) h -= 360;
      if (h < 0) h += 360;
      h /= 60;
      const i = floor2(h);
      const f = h - i;
      const p = v * (1 - s);
      const q = v * (1 - s * f);
      const t = v * (1 - s * (1 - f));
      switch (i) {
        case 0:
          [r, g, b] = [v, t, p];
          break;
        case 1:
          [r, g, b] = [q, v, p];
          break;
        case 2:
          [r, g, b] = [p, v, t];
          break;
        case 3:
          [r, g, b] = [p, q, v];
          break;
        case 4:
          [r, g, b] = [t, p, v];
          break;
        case 5:
          [r, g, b] = [v, p, q];
          break;
      }
    }
    return [r, g, b, args.length > 3 ? args[3] : 1];
  };
  var hsv2rgb_default = hsv2rgb;

  // node_modules/chroma-js/src/io/hsv/rgb2hsv.js
  var { min: min3, max: max3 } = Math;
  var rgb2hsl2 = (...args) => {
    args = unpack_default(args, "rgb");
    let [r, g, b] = args;
    const min_ = min3(r, g, b);
    const max_ = max3(r, g, b);
    const delta = max_ - min_;
    let h, s, v;
    v = max_ / 255;
    if (max_ === 0) {
      h = Number.NaN;
      s = 0;
    } else {
      s = delta / max_;
      if (r === max_) h = (g - b) / delta;
      if (g === max_) h = 2 + (b - r) / delta;
      if (b === max_) h = 4 + (r - g) / delta;
      h *= 60;
      if (h < 0) h += 360;
    }
    return [h, s, v];
  };
  var rgb2hsv_default = rgb2hsl2;

  // node_modules/chroma-js/src/io/hsv/index.js
  Color_default.prototype.hsv = function() {
    return rgb2hsv_default(this._rgb);
  };
  chroma_default.hsv = (...args) => new Color_default(...args, "hsv");
  input_default.format.hsv = hsv2rgb_default;
  input_default.autodetect.push({
    p: 2,
    test: (...args) => {
      args = unpack_default(args, "hsv");
      if (type_default(args) === "array" && args.length === 3) {
        return "hsv";
      }
    }
  });

  // node_modules/chroma-js/src/io/lab/lab-constants.js
  var lab_constants_default = {
    // Corresponds roughly to RGB brighter/darker
    Kn: 18,
    // D65 standard referent
    Xn: 0.95047,
    Yn: 1,
    Zn: 1.08883,
    t0: 0.137931034,
    // 4 / 29
    t1: 0.206896552,
    // 6 / 29
    t2: 0.12841855,
    // 3 * t1 * t1
    t3: 8856452e-9
    // t1 * t1 * t1
  };

  // node_modules/chroma-js/src/io/lab/lab2rgb.js
  var { pow } = Math;
  var lab2rgb = (...args) => {
    args = unpack_default(args, "lab");
    const [l, a, b] = args;
    let x, y, z, r, g, b_;
    y = (l + 16) / 116;
    x = isNaN(a) ? y : y + a / 500;
    z = isNaN(b) ? y : y - b / 200;
    y = lab_constants_default.Yn * lab_xyz(y);
    x = lab_constants_default.Xn * lab_xyz(x);
    z = lab_constants_default.Zn * lab_xyz(z);
    r = xyz_rgb(3.2404542 * x - 1.5371385 * y - 0.4985314 * z);
    g = xyz_rgb(-0.969266 * x + 1.8760108 * y + 0.041556 * z);
    b_ = xyz_rgb(0.0556434 * x - 0.2040259 * y + 1.0572252 * z);
    return [r, g, b_, args.length > 3 ? args[3] : 1];
  };
  var xyz_rgb = (r) => {
    return 255 * (r <= 304e-5 ? 12.92 * r : 1.055 * pow(r, 1 / 2.4) - 0.055);
  };
  var lab_xyz = (t) => {
    return t > lab_constants_default.t1 ? t * t * t : lab_constants_default.t2 * (t - lab_constants_default.t0);
  };
  var lab2rgb_default = lab2rgb;

  // node_modules/chroma-js/src/io/lab/rgb2lab.js
  var { pow: pow2 } = Math;
  var rgb2lab = (...args) => {
    const [r, g, b] = unpack_default(args, "rgb");
    const [x, y, z] = rgb2xyz(r, g, b);
    const l = 116 * y - 16;
    return [l < 0 ? 0 : l, 500 * (x - y), 200 * (y - z)];
  };
  var rgb_xyz = (r) => {
    if ((r /= 255) <= 0.04045) return r / 12.92;
    return pow2((r + 0.055) / 1.055, 2.4);
  };
  var xyz_lab = (t) => {
    if (t > lab_constants_default.t3) return pow2(t, 1 / 3);
    return t / lab_constants_default.t2 + lab_constants_default.t0;
  };
  var rgb2xyz = (r, g, b) => {
    r = rgb_xyz(r);
    g = rgb_xyz(g);
    b = rgb_xyz(b);
    const x = xyz_lab(
      (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / lab_constants_default.Xn
    );
    const y = xyz_lab(
      (0.2126729 * r + 0.7151522 * g + 0.072175 * b) / lab_constants_default.Yn
    );
    const z = xyz_lab(
      (0.0193339 * r + 0.119192 * g + 0.9503041 * b) / lab_constants_default.Zn
    );
    return [x, y, z];
  };
  var rgb2lab_default = rgb2lab;

  // node_modules/chroma-js/src/io/lab/index.js
  Color_default.prototype.lab = function() {
    return rgb2lab_default(this._rgb);
  };
  chroma_default.lab = (...args) => new Color_default(...args, "lab");
  input_default.format.lab = lab2rgb_default;
  input_default.autodetect.push({
    p: 2,
    test: (...args) => {
      args = unpack_default(args, "lab");
      if (type_default(args) === "array" && args.length === 3) {
        return "lab";
      }
    }
  });

  // node_modules/chroma-js/src/io/lch/lch2lab.js
  var { sin, cos: cos2 } = Math;
  var lch2lab = (...args) => {
    let [l, c, h] = unpack_default(args, "lch");
    if (isNaN(h)) h = 0;
    h = h * DEG2RAD;
    return [l, cos2(h) * c, sin(h) * c];
  };
  var lch2lab_default = lch2lab;

  // node_modules/chroma-js/src/io/lch/lch2rgb.js
  var lch2rgb = (...args) => {
    args = unpack_default(args, "lch");
    const [l, c, h] = args;
    const [L, a, b_] = lch2lab_default(l, c, h);
    const [r, g, b] = lab2rgb_default(L, a, b_);
    return [r, g, b, args.length > 3 ? args[3] : 1];
  };
  var lch2rgb_default = lch2rgb;

  // node_modules/chroma-js/src/io/lch/hcl2rgb.js
  var hcl2rgb = (...args) => {
    const hcl = unpack_default(args, "hcl").reverse();
    return lch2rgb_default(...hcl);
  };
  var hcl2rgb_default = hcl2rgb;

  // node_modules/chroma-js/src/io/lch/lab2lch.js
  var { sqrt: sqrt2, atan2, round: round5 } = Math;
  var lab2lch = (...args) => {
    const [l, a, b] = unpack_default(args, "lab");
    const c = sqrt2(a * a + b * b);
    let h = (atan2(b, a) * RAD2DEG + 360) % 360;
    if (round5(c * 1e4) === 0) h = Number.NaN;
    return [l, c, h];
  };
  var lab2lch_default = lab2lch;

  // node_modules/chroma-js/src/io/lch/rgb2lch.js
  var rgb2lch = (...args) => {
    const [r, g, b] = unpack_default(args, "rgb");
    const [l, a, b_] = rgb2lab_default(r, g, b);
    return lab2lch_default(l, a, b_);
  };
  var rgb2lch_default = rgb2lch;

  // node_modules/chroma-js/src/io/lch/index.js
  Color_default.prototype.lch = function() {
    return rgb2lch_default(this._rgb);
  };
  Color_default.prototype.hcl = function() {
    return rgb2lch_default(this._rgb).reverse();
  };
  chroma_default.lch = (...args) => new Color_default(...args, "lch");
  chroma_default.hcl = (...args) => new Color_default(...args, "hcl");
  input_default.format.lch = lch2rgb_default;
  input_default.format.hcl = hcl2rgb_default;
  ["lch", "hcl"].forEach(
    (m) => input_default.autodetect.push({
      p: 2,
      test: (...args) => {
        args = unpack_default(args, m);
        if (type_default(args) === "array" && args.length === 3) {
          return m;
        }
      }
    })
  );

  // node_modules/chroma-js/src/colors/w3cx11.js
  var w3cx11 = {
    aliceblue: "#f0f8ff",
    antiquewhite: "#faebd7",
    aqua: "#00ffff",
    aquamarine: "#7fffd4",
    azure: "#f0ffff",
    beige: "#f5f5dc",
    bisque: "#ffe4c4",
    black: "#000000",
    blanchedalmond: "#ffebcd",
    blue: "#0000ff",
    blueviolet: "#8a2be2",
    brown: "#a52a2a",
    burlywood: "#deb887",
    cadetblue: "#5f9ea0",
    chartreuse: "#7fff00",
    chocolate: "#d2691e",
    coral: "#ff7f50",
    cornflowerblue: "#6495ed",
    cornsilk: "#fff8dc",
    crimson: "#dc143c",
    cyan: "#00ffff",
    darkblue: "#00008b",
    darkcyan: "#008b8b",
    darkgoldenrod: "#b8860b",
    darkgray: "#a9a9a9",
    darkgreen: "#006400",
    darkgrey: "#a9a9a9",
    darkkhaki: "#bdb76b",
    darkmagenta: "#8b008b",
    darkolivegreen: "#556b2f",
    darkorange: "#ff8c00",
    darkorchid: "#9932cc",
    darkred: "#8b0000",
    darksalmon: "#e9967a",
    darkseagreen: "#8fbc8f",
    darkslateblue: "#483d8b",
    darkslategray: "#2f4f4f",
    darkslategrey: "#2f4f4f",
    darkturquoise: "#00ced1",
    darkviolet: "#9400d3",
    deeppink: "#ff1493",
    deepskyblue: "#00bfff",
    dimgray: "#696969",
    dimgrey: "#696969",
    dodgerblue: "#1e90ff",
    firebrick: "#b22222",
    floralwhite: "#fffaf0",
    forestgreen: "#228b22",
    fuchsia: "#ff00ff",
    gainsboro: "#dcdcdc",
    ghostwhite: "#f8f8ff",
    gold: "#ffd700",
    goldenrod: "#daa520",
    gray: "#808080",
    green: "#008000",
    greenyellow: "#adff2f",
    grey: "#808080",
    honeydew: "#f0fff0",
    hotpink: "#ff69b4",
    indianred: "#cd5c5c",
    indigo: "#4b0082",
    ivory: "#fffff0",
    khaki: "#f0e68c",
    laserlemon: "#ffff54",
    lavender: "#e6e6fa",
    lavenderblush: "#fff0f5",
    lawngreen: "#7cfc00",
    lemonchiffon: "#fffacd",
    lightblue: "#add8e6",
    lightcoral: "#f08080",
    lightcyan: "#e0ffff",
    lightgoldenrod: "#fafad2",
    lightgoldenrodyellow: "#fafad2",
    lightgray: "#d3d3d3",
    lightgreen: "#90ee90",
    lightgrey: "#d3d3d3",
    lightpink: "#ffb6c1",
    lightsalmon: "#ffa07a",
    lightseagreen: "#20b2aa",
    lightskyblue: "#87cefa",
    lightslategray: "#778899",
    lightslategrey: "#778899",
    lightsteelblue: "#b0c4de",
    lightyellow: "#ffffe0",
    lime: "#00ff00",
    limegreen: "#32cd32",
    linen: "#faf0e6",
    magenta: "#ff00ff",
    maroon: "#800000",
    maroon2: "#7f0000",
    maroon3: "#b03060",
    mediumaquamarine: "#66cdaa",
    mediumblue: "#0000cd",
    mediumorchid: "#ba55d3",
    mediumpurple: "#9370db",
    mediumseagreen: "#3cb371",
    mediumslateblue: "#7b68ee",
    mediumspringgreen: "#00fa9a",
    mediumturquoise: "#48d1cc",
    mediumvioletred: "#c71585",
    midnightblue: "#191970",
    mintcream: "#f5fffa",
    mistyrose: "#ffe4e1",
    moccasin: "#ffe4b5",
    navajowhite: "#ffdead",
    navy: "#000080",
    oldlace: "#fdf5e6",
    olive: "#808000",
    olivedrab: "#6b8e23",
    orange: "#ffa500",
    orangered: "#ff4500",
    orchid: "#da70d6",
    palegoldenrod: "#eee8aa",
    palegreen: "#98fb98",
    paleturquoise: "#afeeee",
    palevioletred: "#db7093",
    papayawhip: "#ffefd5",
    peachpuff: "#ffdab9",
    peru: "#cd853f",
    pink: "#ffc0cb",
    plum: "#dda0dd",
    powderblue: "#b0e0e6",
    purple: "#800080",
    purple2: "#7f007f",
    purple3: "#a020f0",
    rebeccapurple: "#663399",
    red: "#ff0000",
    rosybrown: "#bc8f8f",
    royalblue: "#4169e1",
    saddlebrown: "#8b4513",
    salmon: "#fa8072",
    sandybrown: "#f4a460",
    seagreen: "#2e8b57",
    seashell: "#fff5ee",
    sienna: "#a0522d",
    silver: "#c0c0c0",
    skyblue: "#87ceeb",
    slateblue: "#6a5acd",
    slategray: "#708090",
    slategrey: "#708090",
    snow: "#fffafa",
    springgreen: "#00ff7f",
    steelblue: "#4682b4",
    tan: "#d2b48c",
    teal: "#008080",
    thistle: "#d8bfd8",
    tomato: "#ff6347",
    turquoise: "#40e0d0",
    violet: "#ee82ee",
    wheat: "#f5deb3",
    white: "#ffffff",
    whitesmoke: "#f5f5f5",
    yellow: "#ffff00",
    yellowgreen: "#9acd32"
  };
  var w3cx11_default = w3cx11;

  // node_modules/chroma-js/src/io/named/index.js
  Color_default.prototype.name = function() {
    const hex = rgb2hex_default(this._rgb, "rgb");
    for (let n of Object.keys(w3cx11_default)) {
      if (w3cx11_default[n] === hex) return n.toLowerCase();
    }
    return hex;
  };
  input_default.format.named = (name) => {
    name = name.toLowerCase();
    if (w3cx11_default[name]) return hex2rgb_default(w3cx11_default[name]);
    throw new Error("unknown color name: " + name);
  };
  input_default.autodetect.push({
    p: 5,
    test: (h, ...rest) => {
      if (!rest.length && type_default(h) === "string" && w3cx11_default[h.toLowerCase()]) {
        return "named";
      }
    }
  });

  // node_modules/chroma-js/src/io/num/num2rgb.js
  var num2rgb = (num2) => {
    if (type_default(num2) == "number" && num2 >= 0 && num2 <= 16777215) {
      const r = num2 >> 16;
      const g = num2 >> 8 & 255;
      const b = num2 & 255;
      return [r, g, b, 1];
    }
    throw new Error("unknown num color: " + num2);
  };
  var num2rgb_default = num2rgb;

  // node_modules/chroma-js/src/io/num/rgb2num.js
  var rgb2num = (...args) => {
    const [r, g, b] = unpack_default(args, "rgb");
    return (r << 16) + (g << 8) + b;
  };
  var rgb2num_default = rgb2num;

  // node_modules/chroma-js/src/io/num/index.js
  Color_default.prototype.num = function() {
    return rgb2num_default(this._rgb);
  };
  chroma_default.num = (...args) => new Color_default(...args, "num");
  input_default.format.num = num2rgb_default;
  input_default.autodetect.push({
    p: 5,
    test: (...args) => {
      if (args.length === 1 && type_default(args[0]) === "number" && args[0] >= 0 && args[0] <= 16777215) {
        return "num";
      }
    }
  });

  // node_modules/chroma-js/src/io/rgb/index.js
  var { round: round6 } = Math;
  Color_default.prototype.rgb = function(rnd2 = true) {
    if (rnd2 === false) return this._rgb.slice(0, 3);
    return this._rgb.slice(0, 3).map(round6);
  };
  Color_default.prototype.rgba = function(rnd2 = true) {
    return this._rgb.slice(0, 4).map((v, i) => {
      return i < 3 ? rnd2 === false ? v : round6(v) : v;
    });
  };
  chroma_default.rgb = (...args) => new Color_default(...args, "rgb");
  input_default.format.rgb = (...args) => {
    const rgba = unpack_default(args, "rgba");
    if (rgba[3] === void 0) rgba[3] = 1;
    return rgba;
  };
  input_default.autodetect.push({
    p: 3,
    test: (...args) => {
      args = unpack_default(args, "rgba");
      if (type_default(args) === "array" && (args.length === 3 || args.length === 4 && type_default(args[3]) == "number" && args[3] >= 0 && args[3] <= 1)) {
        return "rgb";
      }
    }
  });

  // node_modules/chroma-js/src/io/temp/temperature2rgb.js
  var { log } = Math;
  var temperature2rgb = (kelvin) => {
    const temp = kelvin / 100;
    let r, g, b;
    if (temp < 66) {
      r = 255;
      g = temp < 6 ? 0 : -155.25485562709179 - 0.44596950469579133 * (g = temp - 2) + 104.49216199393888 * log(g);
      b = temp < 20 ? 0 : -254.76935184120902 + 0.8274096064007395 * (b = temp - 10) + 115.67994401066147 * log(b);
    } else {
      r = 351.97690566805693 + 0.114206453784165 * (r = temp - 55) - 40.25366309332127 * log(r);
      g = 325.4494125711974 + 0.07943456536662342 * (g = temp - 50) - 28.0852963507957 * log(g);
      b = 255;
    }
    return [r, g, b, 1];
  };
  var temperature2rgb_default = temperature2rgb;

  // node_modules/chroma-js/src/io/temp/rgb2temperature.js
  var { round: round7 } = Math;
  var rgb2temperature = (...args) => {
    const rgb2 = unpack_default(args, "rgb");
    const r = rgb2[0], b = rgb2[2];
    let minTemp = 1e3;
    let maxTemp = 4e4;
    const eps = 0.4;
    let temp;
    while (maxTemp - minTemp > eps) {
      temp = (maxTemp + minTemp) * 0.5;
      const rgb3 = temperature2rgb_default(temp);
      if (rgb3[2] / rgb3[0] >= b / r) {
        maxTemp = temp;
      } else {
        minTemp = temp;
      }
    }
    return round7(temp);
  };
  var rgb2temperature_default = rgb2temperature;

  // node_modules/chroma-js/src/io/temp/index.js
  Color_default.prototype.temp = Color_default.prototype.kelvin = Color_default.prototype.temperature = function() {
    return rgb2temperature_default(this._rgb);
  };
  chroma_default.temp = chroma_default.kelvin = chroma_default.temperature = (...args) => new Color_default(...args, "temp");
  input_default.format.temp = input_default.format.kelvin = input_default.format.temperature = temperature2rgb_default;

  // node_modules/chroma-js/src/io/oklab/oklab2rgb.js
  var { pow: pow3, sign } = Math;
  var oklab2rgb = (...args) => {
    args = unpack_default(args, "lab");
    const [L, a, b] = args;
    const l = pow3(L + 0.3963377774 * a + 0.2158037573 * b, 3);
    const m = pow3(L - 0.1055613458 * a - 0.0638541728 * b, 3);
    const s = pow3(L - 0.0894841775 * a - 1.291485548 * b, 3);
    return [
      255 * lrgb2rgb(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s),
      255 * lrgb2rgb(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s),
      255 * lrgb2rgb(-0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s),
      args.length > 3 ? args[3] : 1
    ];
  };
  var oklab2rgb_default = oklab2rgb;
  function lrgb2rgb(c) {
    const abs3 = Math.abs(c);
    if (abs3 > 31308e-7) {
      return (sign(c) || 1) * (1.055 * pow3(abs3, 1 / 2.4) - 0.055);
    }
    return c * 12.92;
  }

  // node_modules/chroma-js/src/io/oklab/rgb2oklab.js
  var { cbrt, pow: pow4, sign: sign2 } = Math;
  var rgb2oklab = (...args) => {
    const [r, g, b] = unpack_default(args, "rgb");
    const [lr, lg, lb] = [
      rgb2lrgb(r / 255),
      rgb2lrgb(g / 255),
      rgb2lrgb(b / 255)
    ];
    const l = cbrt(0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb);
    const m = cbrt(0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb);
    const s = cbrt(0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb);
    return [
      0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
      1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
      0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s
    ];
  };
  var rgb2oklab_default = rgb2oklab;
  function rgb2lrgb(c) {
    const abs3 = Math.abs(c);
    if (abs3 < 0.04045) {
      return c / 12.92;
    }
    return (sign2(c) || 1) * pow4((abs3 + 0.055) / 1.055, 2.4);
  }

  // node_modules/chroma-js/src/io/oklab/index.js
  Color_default.prototype.oklab = function() {
    return rgb2oklab_default(this._rgb);
  };
  chroma_default.oklab = (...args) => new Color_default(...args, "oklab");
  input_default.format.oklab = oklab2rgb_default;
  input_default.autodetect.push({
    p: 3,
    test: (...args) => {
      args = unpack_default(args, "oklab");
      if (type_default(args) === "array" && args.length === 3) {
        return "oklab";
      }
    }
  });

  // node_modules/chroma-js/src/io/oklch/oklch2rgb.js
  var oklch2rgb = (...args) => {
    args = unpack_default(args, "lch");
    const [l, c, h] = args;
    const [L, a, b_] = lch2lab_default(l, c, h);
    const [r, g, b] = oklab2rgb_default(L, a, b_);
    return [r, g, b, args.length > 3 ? args[3] : 1];
  };
  var oklch2rgb_default = oklch2rgb;

  // node_modules/chroma-js/src/io/oklch/rgb2oklch.js
  var rgb2oklch = (...args) => {
    const [r, g, b] = unpack_default(args, "rgb");
    const [l, a, b_] = rgb2oklab_default(r, g, b);
    return lab2lch_default(l, a, b_);
  };
  var rgb2oklch_default = rgb2oklch;

  // node_modules/chroma-js/src/io/oklch/index.js
  Color_default.prototype.oklch = function() {
    return rgb2oklch_default(this._rgb);
  };
  chroma_default.oklch = (...args) => new Color_default(...args, "oklch");
  input_default.format.oklch = oklch2rgb_default;
  input_default.autodetect.push({
    p: 3,
    test: (...args) => {
      args = unpack_default(args, "oklch");
      if (type_default(args) === "array" && args.length === 3) {
        return "oklch";
      }
    }
  });

  // node_modules/chroma-js/src/ops/alpha.js
  Color_default.prototype.alpha = function(a, mutate = false) {
    if (a !== void 0 && type_default(a) === "number") {
      if (mutate) {
        this._rgb[3] = a;
        return this;
      }
      return new Color_default([this._rgb[0], this._rgb[1], this._rgb[2], a], "rgb");
    }
    return this._rgb[3];
  };

  // node_modules/chroma-js/src/ops/clipped.js
  Color_default.prototype.clipped = function() {
    return this._rgb._clipped || false;
  };

  // node_modules/chroma-js/src/ops/darken.js
  Color_default.prototype.darken = function(amount = 1) {
    const me = this;
    const lab2 = me.lab();
    lab2[0] -= lab_constants_default.Kn * amount;
    return new Color_default(lab2, "lab").alpha(me.alpha(), true);
  };
  Color_default.prototype.brighten = function(amount = 1) {
    return this.darken(-amount);
  };
  Color_default.prototype.darker = Color_default.prototype.darken;
  Color_default.prototype.brighter = Color_default.prototype.brighten;

  // node_modules/chroma-js/src/ops/get.js
  Color_default.prototype.get = function(mc) {
    const [mode, channel] = mc.split(".");
    const src = this[mode]();
    if (channel) {
      const i = mode.indexOf(channel) - (mode.substr(0, 2) === "ok" ? 2 : 0);
      if (i > -1) return src[i];
      throw new Error(`unknown channel ${channel} in mode ${mode}`);
    } else {
      return src;
    }
  };

  // node_modules/chroma-js/src/ops/luminance.js
  var { pow: pow5 } = Math;
  var EPS = 1e-7;
  var MAX_ITER = 20;
  Color_default.prototype.luminance = function(lum, mode = "rgb") {
    if (lum !== void 0 && type_default(lum) === "number") {
      if (lum === 0) {
        return new Color_default([0, 0, 0, this._rgb[3]], "rgb");
      }
      if (lum === 1) {
        return new Color_default([255, 255, 255, this._rgb[3]], "rgb");
      }
      let cur_lum = this.luminance();
      let max_iter = MAX_ITER;
      const test = (low, high) => {
        const mid = low.interpolate(high, 0.5, mode);
        const lm = mid.luminance();
        if (Math.abs(lum - lm) < EPS || !max_iter--) {
          return mid;
        }
        return lm > lum ? test(low, mid) : test(mid, high);
      };
      const rgb2 = (cur_lum > lum ? test(new Color_default([0, 0, 0]), this) : test(this, new Color_default([255, 255, 255]))).rgb();
      return new Color_default([...rgb2, this._rgb[3]]);
    }
    return rgb2luminance(...this._rgb.slice(0, 3));
  };
  var rgb2luminance = (r, g, b) => {
    r = luminance_x(r);
    g = luminance_x(g);
    b = luminance_x(b);
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  var luminance_x = (x) => {
    x /= 255;
    return x <= 0.03928 ? x / 12.92 : pow5((x + 0.055) / 1.055, 2.4);
  };

  // node_modules/chroma-js/src/interpolator/index.js
  var interpolator_default = {};

  // node_modules/chroma-js/src/generator/mix.js
  var mix_default = (col1, col2, f = 0.5, ...rest) => {
    let mode = rest[0] || "lrgb";
    if (!interpolator_default[mode] && !rest.length) {
      mode = Object.keys(interpolator_default)[0];
    }
    if (!interpolator_default[mode]) {
      throw new Error(`interpolation mode ${mode} is not defined`);
    }
    if (type_default(col1) !== "object") col1 = new Color_default(col1);
    if (type_default(col2) !== "object") col2 = new Color_default(col2);
    return interpolator_default[mode](col1, col2, f).alpha(
      col1.alpha() + f * (col2.alpha() - col1.alpha())
    );
  };

  // node_modules/chroma-js/src/ops/mix.js
  Color_default.prototype.mix = Color_default.prototype.interpolate = function(col2, f = 0.5, ...rest) {
    return mix_default(this, col2, f, ...rest);
  };

  // node_modules/chroma-js/src/ops/premultiply.js
  Color_default.prototype.premultiply = function(mutate = false) {
    const rgb2 = this._rgb;
    const a = rgb2[3];
    if (mutate) {
      this._rgb = [rgb2[0] * a, rgb2[1] * a, rgb2[2] * a, a];
      return this;
    } else {
      return new Color_default([rgb2[0] * a, rgb2[1] * a, rgb2[2] * a, a], "rgb");
    }
  };

  // node_modules/chroma-js/src/ops/saturate.js
  Color_default.prototype.saturate = function(amount = 1) {
    const me = this;
    const lch2 = me.lch();
    lch2[1] += lab_constants_default.Kn * amount;
    if (lch2[1] < 0) lch2[1] = 0;
    return new Color_default(lch2, "lch").alpha(me.alpha(), true);
  };
  Color_default.prototype.desaturate = function(amount = 1) {
    return this.saturate(-amount);
  };

  // node_modules/chroma-js/src/ops/set.js
  Color_default.prototype.set = function(mc, value, mutate = false) {
    const [mode, channel] = mc.split(".");
    const src = this[mode]();
    if (channel) {
      const i = mode.indexOf(channel) - (mode.substr(0, 2) === "ok" ? 2 : 0);
      if (i > -1) {
        if (type_default(value) == "string") {
          switch (value.charAt(0)) {
            case "+":
              src[i] += +value;
              break;
            case "-":
              src[i] += +value;
              break;
            case "*":
              src[i] *= +value.substr(1);
              break;
            case "/":
              src[i] /= +value.substr(1);
              break;
            default:
              src[i] = +value;
          }
        } else if (type_default(value) === "number") {
          src[i] = value;
        } else {
          throw new Error(`unsupported value for Color.set`);
        }
        const out = new Color_default(src, mode);
        if (mutate) {
          this._rgb = out._rgb;
          return this;
        }
        return out;
      }
      throw new Error(`unknown channel ${channel} in mode ${mode}`);
    } else {
      return src;
    }
  };

  // node_modules/chroma-js/src/ops/shade.js
  Color_default.prototype.tint = function(f = 0.5, ...rest) {
    return mix_default(this, "white", f, ...rest);
  };
  Color_default.prototype.shade = function(f = 0.5, ...rest) {
    return mix_default(this, "black", f, ...rest);
  };

  // node_modules/chroma-js/src/interpolator/rgb.js
  var rgb = (col1, col2, f) => {
    const xyz0 = col1._rgb;
    const xyz1 = col2._rgb;
    return new Color_default(
      xyz0[0] + f * (xyz1[0] - xyz0[0]),
      xyz0[1] + f * (xyz1[1] - xyz0[1]),
      xyz0[2] + f * (xyz1[2] - xyz0[2]),
      "rgb"
    );
  };
  interpolator_default.rgb = rgb;

  // node_modules/chroma-js/src/interpolator/lrgb.js
  var { sqrt: sqrt3, pow: pow6 } = Math;
  var lrgb = (col1, col2, f) => {
    const [x1, y1, z1] = col1._rgb;
    const [x2, y2, z2] = col2._rgb;
    return new Color_default(
      sqrt3(pow6(x1, 2) * (1 - f) + pow6(x2, 2) * f),
      sqrt3(pow6(y1, 2) * (1 - f) + pow6(y2, 2) * f),
      sqrt3(pow6(z1, 2) * (1 - f) + pow6(z2, 2) * f),
      "rgb"
    );
  };
  interpolator_default.lrgb = lrgb;

  // node_modules/chroma-js/src/interpolator/lab.js
  var lab = (col1, col2, f) => {
    const xyz0 = col1.lab();
    const xyz1 = col2.lab();
    return new Color_default(
      xyz0[0] + f * (xyz1[0] - xyz0[0]),
      xyz0[1] + f * (xyz1[1] - xyz0[1]),
      xyz0[2] + f * (xyz1[2] - xyz0[2]),
      "lab"
    );
  };
  interpolator_default.lab = lab;

  // node_modules/chroma-js/src/interpolator/_hsx.js
  var hsx_default = (col1, col2, f, m) => {
    let xyz0, xyz1;
    if (m === "hsl") {
      xyz0 = col1.hsl();
      xyz1 = col2.hsl();
    } else if (m === "hsv") {
      xyz0 = col1.hsv();
      xyz1 = col2.hsv();
    } else if (m === "hcg") {
      xyz0 = col1.hcg();
      xyz1 = col2.hcg();
    } else if (m === "hsi") {
      xyz0 = col1.hsi();
      xyz1 = col2.hsi();
    } else if (m === "lch" || m === "hcl") {
      m = "hcl";
      xyz0 = col1.hcl();
      xyz1 = col2.hcl();
    } else if (m === "oklch") {
      xyz0 = col1.oklch().reverse();
      xyz1 = col2.oklch().reverse();
    }
    let hue0, hue1, sat0, sat1, lbv0, lbv1;
    if (m.substr(0, 1) === "h" || m === "oklch") {
      [hue0, sat0, lbv0] = xyz0;
      [hue1, sat1, lbv1] = xyz1;
    }
    let sat, hue, lbv, dh;
    if (!isNaN(hue0) && !isNaN(hue1)) {
      if (hue1 > hue0 && hue1 - hue0 > 180) {
        dh = hue1 - (hue0 + 360);
      } else if (hue1 < hue0 && hue0 - hue1 > 180) {
        dh = hue1 + 360 - hue0;
      } else {
        dh = hue1 - hue0;
      }
      hue = hue0 + f * dh;
    } else if (!isNaN(hue0)) {
      hue = hue0;
      if ((lbv1 == 1 || lbv1 == 0) && m != "hsv") sat = sat0;
    } else if (!isNaN(hue1)) {
      hue = hue1;
      if ((lbv0 == 1 || lbv0 == 0) && m != "hsv") sat = sat1;
    } else {
      hue = Number.NaN;
    }
    if (sat === void 0) sat = sat0 + f * (sat1 - sat0);
    lbv = lbv0 + f * (lbv1 - lbv0);
    return m === "oklch" ? new Color_default([lbv, sat, hue], m) : new Color_default([hue, sat, lbv], m);
  };

  // node_modules/chroma-js/src/interpolator/lch.js
  var lch = (col1, col2, f) => {
    return hsx_default(col1, col2, f, "lch");
  };
  interpolator_default.lch = lch;
  interpolator_default.hcl = lch;

  // node_modules/chroma-js/src/interpolator/num.js
  var num = (col1, col2, f) => {
    const c1 = col1.num();
    const c2 = col2.num();
    return new Color_default(c1 + f * (c2 - c1), "num");
  };
  interpolator_default.num = num;

  // node_modules/chroma-js/src/interpolator/hcg.js
  var hcg = (col1, col2, f) => {
    return hsx_default(col1, col2, f, "hcg");
  };
  interpolator_default.hcg = hcg;

  // node_modules/chroma-js/src/interpolator/hsi.js
  var hsi = (col1, col2, f) => {
    return hsx_default(col1, col2, f, "hsi");
  };
  interpolator_default.hsi = hsi;

  // node_modules/chroma-js/src/interpolator/hsl.js
  var hsl = (col1, col2, f) => {
    return hsx_default(col1, col2, f, "hsl");
  };
  interpolator_default.hsl = hsl;

  // node_modules/chroma-js/src/interpolator/hsv.js
  var hsv = (col1, col2, f) => {
    return hsx_default(col1, col2, f, "hsv");
  };
  interpolator_default.hsv = hsv;

  // node_modules/chroma-js/src/interpolator/oklab.js
  var oklab = (col1, col2, f) => {
    const xyz0 = col1.oklab();
    const xyz1 = col2.oklab();
    return new Color_default(
      xyz0[0] + f * (xyz1[0] - xyz0[0]),
      xyz0[1] + f * (xyz1[1] - xyz0[1]),
      xyz0[2] + f * (xyz1[2] - xyz0[2]),
      "oklab"
    );
  };
  interpolator_default.oklab = oklab;

  // node_modules/chroma-js/src/interpolator/oklch.js
  var oklch = (col1, col2, f) => {
    return hsx_default(col1, col2, f, "oklch");
  };
  interpolator_default.oklch = oklch;

  // node_modules/chroma-js/src/generator/average.js
  var { pow: pow7, sqrt: sqrt4, PI: PI2, cos: cos3, sin: sin2, atan2: atan22 } = Math;
  var average_default = (colors, mode = "lrgb", weights = null) => {
    const l = colors.length;
    if (!weights) weights = Array.from(new Array(l)).map(() => 1);
    const k = l / weights.reduce(function(a, b) {
      return a + b;
    });
    weights.forEach((w, i) => {
      weights[i] *= k;
    });
    colors = colors.map((c) => new Color_default(c));
    if (mode === "lrgb") {
      return _average_lrgb(colors, weights);
    }
    const first = colors.shift();
    const xyz = first.get(mode);
    const cnt = [];
    let dx = 0;
    let dy = 0;
    for (let i = 0; i < xyz.length; i++) {
      xyz[i] = (xyz[i] || 0) * weights[0];
      cnt.push(isNaN(xyz[i]) ? 0 : weights[0]);
      if (mode.charAt(i) === "h" && !isNaN(xyz[i])) {
        const A = xyz[i] / 180 * PI2;
        dx += cos3(A) * weights[0];
        dy += sin2(A) * weights[0];
      }
    }
    let alpha = first.alpha() * weights[0];
    colors.forEach((c, ci) => {
      const xyz2 = c.get(mode);
      alpha += c.alpha() * weights[ci + 1];
      for (let i = 0; i < xyz.length; i++) {
        if (!isNaN(xyz2[i])) {
          cnt[i] += weights[ci + 1];
          if (mode.charAt(i) === "h") {
            const A = xyz2[i] / 180 * PI2;
            dx += cos3(A) * weights[ci + 1];
            dy += sin2(A) * weights[ci + 1];
          } else {
            xyz[i] += xyz2[i] * weights[ci + 1];
          }
        }
      }
    });
    for (let i = 0; i < xyz.length; i++) {
      if (mode.charAt(i) === "h") {
        let A = atan22(dy / cnt[i], dx / cnt[i]) / PI2 * 180;
        while (A < 0) A += 360;
        while (A >= 360) A -= 360;
        xyz[i] = A;
      } else {
        xyz[i] = xyz[i] / cnt[i];
      }
    }
    alpha /= l;
    return new Color_default(xyz, mode).alpha(alpha > 0.99999 ? 1 : alpha, true);
  };
  var _average_lrgb = (colors, weights) => {
    const l = colors.length;
    const xyz = [0, 0, 0, 0];
    for (let i = 0; i < colors.length; i++) {
      const col = colors[i];
      const f = weights[i] / l;
      const rgb2 = col._rgb;
      xyz[0] += pow7(rgb2[0], 2) * f;
      xyz[1] += pow7(rgb2[1], 2) * f;
      xyz[2] += pow7(rgb2[2], 2) * f;
      xyz[3] += rgb2[3] * f;
    }
    xyz[0] = sqrt4(xyz[0]);
    xyz[1] = sqrt4(xyz[1]);
    xyz[2] = sqrt4(xyz[2]);
    if (xyz[3] > 0.9999999) xyz[3] = 1;
    return new Color_default(clip_rgb_default(xyz));
  };

  // node_modules/chroma-js/src/generator/scale.js
  var { pow: pow8 } = Math;
  function scale_default(colors) {
    let _mode = "rgb";
    let _nacol = chroma_default("#ccc");
    let _spread = 0;
    let _domain = [0, 1];
    let _pos = [];
    let _padding = [0, 0];
    let _classes = false;
    let _colors = [];
    let _out = false;
    let _min = 0;
    let _max = 1;
    let _correctLightness = false;
    let _colorCache = {};
    let _useCache = true;
    let _gamma = 1;
    const setColors = function(colors2) {
      colors2 = colors2 || ["#fff", "#000"];
      if (colors2 && type_default(colors2) === "string" && chroma_default.brewer && chroma_default.brewer[colors2.toLowerCase()]) {
        colors2 = chroma_default.brewer[colors2.toLowerCase()];
      }
      if (type_default(colors2) === "array") {
        if (colors2.length === 1) {
          colors2 = [colors2[0], colors2[0]];
        }
        colors2 = colors2.slice(0);
        for (let c = 0; c < colors2.length; c++) {
          colors2[c] = chroma_default(colors2[c]);
        }
        _pos.length = 0;
        for (let c = 0; c < colors2.length; c++) {
          _pos.push(c / (colors2.length - 1));
        }
      }
      resetCache();
      return _colors = colors2;
    };
    const getClass = function(value) {
      if (_classes != null) {
        const n = _classes.length - 1;
        let i = 0;
        while (i < n && value >= _classes[i]) {
          i++;
        }
        return i - 1;
      }
      return 0;
    };
    let tMapLightness = (t) => t;
    let tMapDomain = (t) => t;
    const getColor = function(val, bypassMap) {
      let col, t;
      if (bypassMap == null) {
        bypassMap = false;
      }
      if (isNaN(val) || val === null) {
        return _nacol;
      }
      if (!bypassMap) {
        if (_classes && _classes.length > 2) {
          const c = getClass(val);
          t = c / (_classes.length - 2);
        } else if (_max !== _min) {
          t = (val - _min) / (_max - _min);
        } else {
          t = 1;
        }
      } else {
        t = val;
      }
      t = tMapDomain(t);
      if (!bypassMap) {
        t = tMapLightness(t);
      }
      if (_gamma !== 1) {
        t = pow8(t, _gamma);
      }
      t = _padding[0] + t * (1 - _padding[0] - _padding[1]);
      t = limit_default(t, 0, 1);
      const k = Math.floor(t * 1e4);
      if (_useCache && _colorCache[k]) {
        col = _colorCache[k];
      } else {
        if (type_default(_colors) === "array") {
          for (let i = 0; i < _pos.length; i++) {
            const p = _pos[i];
            if (t <= p) {
              col = _colors[i];
              break;
            }
            if (t >= p && i === _pos.length - 1) {
              col = _colors[i];
              break;
            }
            if (t > p && t < _pos[i + 1]) {
              t = (t - p) / (_pos[i + 1] - p);
              col = chroma_default.interpolate(
                _colors[i],
                _colors[i + 1],
                t,
                _mode
              );
              break;
            }
          }
        } else if (type_default(_colors) === "function") {
          col = _colors(t);
        }
        if (_useCache) {
          _colorCache[k] = col;
        }
      }
      return col;
    };
    var resetCache = () => _colorCache = {};
    setColors(colors);
    const f = function(v) {
      const c = chroma_default(getColor(v));
      if (_out && c[_out]) {
        return c[_out]();
      } else {
        return c;
      }
    };
    f.classes = function(classes) {
      if (classes != null) {
        if (type_default(classes) === "array") {
          _classes = classes;
          _domain = [classes[0], classes[classes.length - 1]];
        } else {
          const d = chroma_default.analyze(_domain);
          if (classes === 0) {
            _classes = [d.min, d.max];
          } else {
            _classes = chroma_default.limits(d, "e", classes);
          }
        }
        return f;
      }
      return _classes;
    };
    f.domain = function(domain) {
      if (!arguments.length) {
        return _domain;
      }
      _min = domain[0];
      _max = domain[domain.length - 1];
      _pos = [];
      const k = _colors.length;
      if (domain.length === k && _min !== _max) {
        for (let d of Array.from(domain)) {
          _pos.push((d - _min) / (_max - _min));
        }
      } else {
        for (let c = 0; c < k; c++) {
          _pos.push(c / (k - 1));
        }
        if (domain.length > 2) {
          const tOut = domain.map((d, i) => i / (domain.length - 1));
          const tBreaks = domain.map((d) => (d - _min) / (_max - _min));
          if (!tBreaks.every((val, i) => tOut[i] === val)) {
            tMapDomain = (t) => {
              if (t <= 0 || t >= 1) return t;
              let i = 0;
              while (t >= tBreaks[i + 1]) i++;
              const f2 = (t - tBreaks[i]) / (tBreaks[i + 1] - tBreaks[i]);
              const out = tOut[i] + f2 * (tOut[i + 1] - tOut[i]);
              return out;
            };
          }
        }
      }
      _domain = [_min, _max];
      return f;
    };
    f.mode = function(_m) {
      if (!arguments.length) {
        return _mode;
      }
      _mode = _m;
      resetCache();
      return f;
    };
    f.range = function(colors2, _pos2) {
      setColors(colors2, _pos2);
      return f;
    };
    f.out = function(_o) {
      _out = _o;
      return f;
    };
    f.spread = function(val) {
      if (!arguments.length) {
        return _spread;
      }
      _spread = val;
      return f;
    };
    f.correctLightness = function(v) {
      if (v == null) {
        v = true;
      }
      _correctLightness = v;
      resetCache();
      if (_correctLightness) {
        tMapLightness = function(t) {
          const L0 = getColor(0, true).lab()[0];
          const L1 = getColor(1, true).lab()[0];
          const pol = L0 > L1;
          let L_actual = getColor(t, true).lab()[0];
          const L_ideal = L0 + (L1 - L0) * t;
          let L_diff = L_actual - L_ideal;
          let t0 = 0;
          let t1 = 1;
          let max_iter = 20;
          while (Math.abs(L_diff) > 0.01 && max_iter-- > 0) {
            (function() {
              if (pol) {
                L_diff *= -1;
              }
              if (L_diff < 0) {
                t0 = t;
                t += (t1 - t) * 0.5;
              } else {
                t1 = t;
                t += (t0 - t) * 0.5;
              }
              L_actual = getColor(t, true).lab()[0];
              return L_diff = L_actual - L_ideal;
            })();
          }
          return t;
        };
      } else {
        tMapLightness = (t) => t;
      }
      return f;
    };
    f.padding = function(p) {
      if (p != null) {
        if (type_default(p) === "number") {
          p = [p, p];
        }
        _padding = p;
        return f;
      } else {
        return _padding;
      }
    };
    f.colors = function(numColors, out) {
      if (arguments.length < 2) {
        out = "hex";
      }
      let result = [];
      if (arguments.length === 0) {
        result = _colors.slice(0);
      } else if (numColors === 1) {
        result = [f(0.5)];
      } else if (numColors > 1) {
        const dm = _domain[0];
        const dd = _domain[1] - dm;
        result = __range__(0, numColors, false).map(
          (i) => f(dm + i / (numColors - 1) * dd)
        );
      } else {
        colors = [];
        let samples = [];
        if (_classes && _classes.length > 2) {
          for (let i = 1, end = _classes.length, asc = 1 <= end; asc ? i < end : i > end; asc ? i++ : i--) {
            samples.push((_classes[i - 1] + _classes[i]) * 0.5);
          }
        } else {
          samples = _domain;
        }
        result = samples.map((v) => f(v));
      }
      if (chroma_default[out]) {
        result = result.map((c) => c[out]());
      }
      return result;
    };
    f.cache = function(c) {
      if (c != null) {
        _useCache = c;
        return f;
      } else {
        return _useCache;
      }
    };
    f.gamma = function(g) {
      if (g != null) {
        _gamma = g;
        return f;
      } else {
        return _gamma;
      }
    };
    f.nodata = function(d) {
      if (d != null) {
        _nacol = chroma_default(d);
        return f;
      } else {
        return _nacol;
      }
    };
    return f;
  }
  function __range__(left, right, inclusive) {
    let range = [];
    let ascending = left < right;
    let end = !inclusive ? right : ascending ? right + 1 : right - 1;
    for (let i = left; ascending ? i < end : i > end; ascending ? i++ : i--) {
      range.push(i);
    }
    return range;
  }

  // node_modules/chroma-js/src/generator/bezier.js
  var binom_row = function(n) {
    let row = [1, 1];
    for (let i = 1; i < n; i++) {
      let newrow = [1];
      for (let j = 1; j <= row.length; j++) {
        newrow[j] = (row[j] || 0) + row[j - 1];
      }
      row = newrow;
    }
    return row;
  };
  var bezier = function(colors) {
    let I, lab0, lab1, lab2;
    colors = colors.map((c) => new Color_default(c));
    if (colors.length === 2) {
      [lab0, lab1] = colors.map((c) => c.lab());
      I = function(t) {
        const lab3 = [0, 1, 2].map((i) => lab0[i] + t * (lab1[i] - lab0[i]));
        return new Color_default(lab3, "lab");
      };
    } else if (colors.length === 3) {
      [lab0, lab1, lab2] = colors.map((c) => c.lab());
      I = function(t) {
        const lab3 = [0, 1, 2].map(
          (i) => (1 - t) * (1 - t) * lab0[i] + 2 * (1 - t) * t * lab1[i] + t * t * lab2[i]
        );
        return new Color_default(lab3, "lab");
      };
    } else if (colors.length === 4) {
      let lab3;
      [lab0, lab1, lab2, lab3] = colors.map((c) => c.lab());
      I = function(t) {
        const lab4 = [0, 1, 2].map(
          (i) => (1 - t) * (1 - t) * (1 - t) * lab0[i] + 3 * (1 - t) * (1 - t) * t * lab1[i] + 3 * (1 - t) * t * t * lab2[i] + t * t * t * lab3[i]
        );
        return new Color_default(lab4, "lab");
      };
    } else if (colors.length >= 5) {
      let labs, row, n;
      labs = colors.map((c) => c.lab());
      n = colors.length - 1;
      row = binom_row(n);
      I = function(t) {
        const u = 1 - t;
        const lab3 = [0, 1, 2].map(
          (i) => labs.reduce(
            (sum, el, j) => sum + row[j] * u ** (n - j) * t ** j * el[i],
            0
          )
        );
        return new Color_default(lab3, "lab");
      };
    } else {
      throw new RangeError("No point in running bezier with only one color.");
    }
    return I;
  };
  var bezier_default = (colors) => {
    const f = bezier(colors);
    f.scale = () => scale_default(f);
    return f;
  };

  // node_modules/chroma-js/src/generator/blend.js
  var blend = (bottom, top, mode) => {
    if (!blend[mode]) {
      throw new Error("unknown blend mode " + mode);
    }
    return blend[mode](bottom, top);
  };
  var blend_f = (f) => (bottom, top) => {
    const c0 = chroma_default(top).rgb();
    const c1 = chroma_default(bottom).rgb();
    return chroma_default.rgb(f(c0, c1));
  };
  var each = (f) => (c0, c1) => {
    const out = [];
    out[0] = f(c0[0], c1[0]);
    out[1] = f(c0[1], c1[1]);
    out[2] = f(c0[2], c1[2]);
    return out;
  };
  var normal = (a) => a;
  var multiply = (a, b) => a * b / 255;
  var darken = (a, b) => a > b ? b : a;
  var lighten = (a, b) => a > b ? a : b;
  var screen = (a, b) => 255 * (1 - (1 - a / 255) * (1 - b / 255));
  var overlay = (a, b) => b < 128 ? 2 * a * b / 255 : 255 * (1 - 2 * (1 - a / 255) * (1 - b / 255));
  var burn = (a, b) => 255 * (1 - (1 - b / 255) / (a / 255));
  var dodge = (a, b) => {
    if (a === 255) return 255;
    a = 255 * (b / 255) / (1 - a / 255);
    return a > 255 ? 255 : a;
  };
  blend.normal = blend_f(each(normal));
  blend.multiply = blend_f(each(multiply));
  blend.screen = blend_f(each(screen));
  blend.overlay = blend_f(each(overlay));
  blend.darken = blend_f(each(darken));
  blend.lighten = blend_f(each(lighten));
  blend.dodge = blend_f(each(dodge));
  blend.burn = blend_f(each(burn));
  var blend_default = blend;

  // node_modules/chroma-js/src/generator/cubehelix.js
  var { pow: pow9, sin: sin3, cos: cos4 } = Math;
  function cubehelix_default(start = 300, rotations = -1.5, hue = 1, gamma = 1, lightness = [0, 1]) {
    let dh = 0, dl;
    if (type_default(lightness) === "array") {
      dl = lightness[1] - lightness[0];
    } else {
      dl = 0;
      lightness = [lightness, lightness];
    }
    const f = function(fract) {
      const a = TWOPI * ((start + 120) / 360 + rotations * fract);
      const l = pow9(lightness[0] + dl * fract, gamma);
      const h = dh !== 0 ? hue[0] + fract * dh : hue;
      const amp = h * l * (1 - l) / 2;
      const cos_a = cos4(a);
      const sin_a = sin3(a);
      const r = l + amp * (-0.14861 * cos_a + 1.78277 * sin_a);
      const g = l + amp * (-0.29227 * cos_a - 0.90649 * sin_a);
      const b = l + amp * (1.97294 * cos_a);
      return chroma_default(clip_rgb_default([r * 255, g * 255, b * 255, 1]));
    };
    f.start = function(s) {
      if (s == null) {
        return start;
      }
      start = s;
      return f;
    };
    f.rotations = function(r) {
      if (r == null) {
        return rotations;
      }
      rotations = r;
      return f;
    };
    f.gamma = function(g) {
      if (g == null) {
        return gamma;
      }
      gamma = g;
      return f;
    };
    f.hue = function(h) {
      if (h == null) {
        return hue;
      }
      hue = h;
      if (type_default(hue) === "array") {
        dh = hue[1] - hue[0];
        if (dh === 0) {
          hue = hue[1];
        }
      } else {
        dh = 0;
      }
      return f;
    };
    f.lightness = function(h) {
      if (h == null) {
        return lightness;
      }
      if (type_default(h) === "array") {
        lightness = h;
        dl = h[1] - h[0];
      } else {
        lightness = [h, h];
        dl = 0;
      }
      return f;
    };
    f.scale = () => chroma_default.scale(f);
    f.hue(hue);
    return f;
  }

  // node_modules/chroma-js/src/generator/random.js
  var digits = "0123456789abcdef";
  var { floor: floor3, random } = Math;
  var random_default = () => {
    let code = "#";
    for (let i = 0; i < 6; i++) {
      code += digits.charAt(floor3(random() * 16));
    }
    return new Color_default(code, "hex");
  };

  // node_modules/chroma-js/src/utils/analyze.js
  var { log: log2, pow: pow10, floor: floor4, abs } = Math;
  function analyze(data, key = null) {
    const r = {
      min: Number.MAX_VALUE,
      max: Number.MAX_VALUE * -1,
      sum: 0,
      values: [],
      count: 0
    };
    if (type_default(data) === "object") {
      data = Object.values(data);
    }
    data.forEach((val) => {
      if (key && type_default(val) === "object") val = val[key];
      if (val !== void 0 && val !== null && !isNaN(val)) {
        r.values.push(val);
        r.sum += val;
        if (val < r.min) r.min = val;
        if (val > r.max) r.max = val;
        r.count += 1;
      }
    });
    r.domain = [r.min, r.max];
    r.limits = (mode, num2) => limits(r, mode, num2);
    return r;
  }
  function limits(data, mode = "equal", num2 = 7) {
    if (type_default(data) == "array") {
      data = analyze(data);
    }
    const { min: min5, max: max5 } = data;
    const values = data.values.sort((a, b) => a - b);
    if (num2 === 1) {
      return [min5, max5];
    }
    const limits2 = [];
    if (mode.substr(0, 1) === "c") {
      limits2.push(min5);
      limits2.push(max5);
    }
    if (mode.substr(0, 1) === "e") {
      limits2.push(min5);
      for (let i = 1; i < num2; i++) {
        limits2.push(min5 + i / num2 * (max5 - min5));
      }
      limits2.push(max5);
    } else if (mode.substr(0, 1) === "l") {
      if (min5 <= 0) {
        throw new Error(
          "Logarithmic scales are only possible for values > 0"
        );
      }
      const min_log = Math.LOG10E * log2(min5);
      const max_log = Math.LOG10E * log2(max5);
      limits2.push(min5);
      for (let i = 1; i < num2; i++) {
        limits2.push(pow10(10, min_log + i / num2 * (max_log - min_log)));
      }
      limits2.push(max5);
    } else if (mode.substr(0, 1) === "q") {
      limits2.push(min5);
      for (let i = 1; i < num2; i++) {
        const p = (values.length - 1) * i / num2;
        const pb = floor4(p);
        if (pb === p) {
          limits2.push(values[pb]);
        } else {
          const pr = p - pb;
          limits2.push(values[pb] * (1 - pr) + values[pb + 1] * pr);
        }
      }
      limits2.push(max5);
    } else if (mode.substr(0, 1) === "k") {
      let cluster;
      const n = values.length;
      const assignments = new Array(n);
      const clusterSizes = new Array(num2);
      let repeat = true;
      let nb_iters = 0;
      let centroids = null;
      centroids = [];
      centroids.push(min5);
      for (let i = 1; i < num2; i++) {
        centroids.push(min5 + i / num2 * (max5 - min5));
      }
      centroids.push(max5);
      while (repeat) {
        for (let j = 0; j < num2; j++) {
          clusterSizes[j] = 0;
        }
        for (let i = 0; i < n; i++) {
          const value = values[i];
          let mindist = Number.MAX_VALUE;
          let best;
          for (let j = 0; j < num2; j++) {
            const dist = abs(centroids[j] - value);
            if (dist < mindist) {
              mindist = dist;
              best = j;
            }
            clusterSizes[best]++;
            assignments[i] = best;
          }
        }
        const newCentroids = new Array(num2);
        for (let j = 0; j < num2; j++) {
          newCentroids[j] = null;
        }
        for (let i = 0; i < n; i++) {
          cluster = assignments[i];
          if (newCentroids[cluster] === null) {
            newCentroids[cluster] = values[i];
          } else {
            newCentroids[cluster] += values[i];
          }
        }
        for (let j = 0; j < num2; j++) {
          newCentroids[j] *= 1 / clusterSizes[j];
        }
        repeat = false;
        for (let j = 0; j < num2; j++) {
          if (newCentroids[j] !== centroids[j]) {
            repeat = true;
            break;
          }
        }
        centroids = newCentroids;
        nb_iters++;
        if (nb_iters > 200) {
          repeat = false;
        }
      }
      const kClusters = {};
      for (let j = 0; j < num2; j++) {
        kClusters[j] = [];
      }
      for (let i = 0; i < n; i++) {
        cluster = assignments[i];
        kClusters[cluster].push(values[i]);
      }
      let tmpKMeansBreaks = [];
      for (let j = 0; j < num2; j++) {
        tmpKMeansBreaks.push(kClusters[j][0]);
        tmpKMeansBreaks.push(kClusters[j][kClusters[j].length - 1]);
      }
      tmpKMeansBreaks = tmpKMeansBreaks.sort((a, b) => a - b);
      limits2.push(tmpKMeansBreaks[0]);
      for (let i = 1; i < tmpKMeansBreaks.length; i += 2) {
        const v = tmpKMeansBreaks[i];
        if (!isNaN(v) && limits2.indexOf(v) === -1) {
          limits2.push(v);
        }
      }
    }
    return limits2;
  }

  // node_modules/chroma-js/src/utils/contrast.js
  var contrast_default = (a, b) => {
    a = new Color_default(a);
    b = new Color_default(b);
    const l1 = a.luminance();
    const l2 = b.luminance();
    return l1 > l2 ? (l1 + 0.05) / (l2 + 0.05) : (l2 + 0.05) / (l1 + 0.05);
  };

  // node_modules/chroma-js/src/utils/delta-e.js
  var { sqrt: sqrt5, pow: pow11, min: min4, max: max4, atan2: atan23, abs: abs2, cos: cos5, sin: sin4, exp, PI: PI3 } = Math;
  function delta_e_default(a, b, Kl = 1, Kc = 1, Kh = 1) {
    var rad2deg = function(rad) {
      return 360 * rad / (2 * PI3);
    };
    var deg2rad = function(deg) {
      return 2 * PI3 * deg / 360;
    };
    a = new Color_default(a);
    b = new Color_default(b);
    const [L1, a1, b1] = Array.from(a.lab());
    const [L2, a2, b2] = Array.from(b.lab());
    const avgL = (L1 + L2) / 2;
    const C1 = sqrt5(pow11(a1, 2) + pow11(b1, 2));
    const C2 = sqrt5(pow11(a2, 2) + pow11(b2, 2));
    const avgC = (C1 + C2) / 2;
    const G = 0.5 * (1 - sqrt5(pow11(avgC, 7) / (pow11(avgC, 7) + pow11(25, 7))));
    const a1p = a1 * (1 + G);
    const a2p = a2 * (1 + G);
    const C1p = sqrt5(pow11(a1p, 2) + pow11(b1, 2));
    const C2p = sqrt5(pow11(a2p, 2) + pow11(b2, 2));
    const avgCp = (C1p + C2p) / 2;
    const arctan1 = rad2deg(atan23(b1, a1p));
    const arctan2 = rad2deg(atan23(b2, a2p));
    const h1p = arctan1 >= 0 ? arctan1 : arctan1 + 360;
    const h2p = arctan2 >= 0 ? arctan2 : arctan2 + 360;
    const avgHp = abs2(h1p - h2p) > 180 ? (h1p + h2p + 360) / 2 : (h1p + h2p) / 2;
    const T = 1 - 0.17 * cos5(deg2rad(avgHp - 30)) + 0.24 * cos5(deg2rad(2 * avgHp)) + 0.32 * cos5(deg2rad(3 * avgHp + 6)) - 0.2 * cos5(deg2rad(4 * avgHp - 63));
    let deltaHp = h2p - h1p;
    deltaHp = abs2(deltaHp) <= 180 ? deltaHp : h2p <= h1p ? deltaHp + 360 : deltaHp - 360;
    deltaHp = 2 * sqrt5(C1p * C2p) * sin4(deg2rad(deltaHp) / 2);
    const deltaL = L2 - L1;
    const deltaCp = C2p - C1p;
    const sl = 1 + 0.015 * pow11(avgL - 50, 2) / sqrt5(20 + pow11(avgL - 50, 2));
    const sc = 1 + 0.045 * avgCp;
    const sh = 1 + 0.015 * avgCp * T;
    const deltaTheta = 30 * exp(-pow11((avgHp - 275) / 25, 2));
    const Rc = 2 * sqrt5(pow11(avgCp, 7) / (pow11(avgCp, 7) + pow11(25, 7)));
    const Rt = -Rc * sin4(2 * deg2rad(deltaTheta));
    const result = sqrt5(
      pow11(deltaL / (Kl * sl), 2) + pow11(deltaCp / (Kc * sc), 2) + pow11(deltaHp / (Kh * sh), 2) + Rt * (deltaCp / (Kc * sc)) * (deltaHp / (Kh * sh))
    );
    return max4(0, min4(100, result));
  }

  // node_modules/chroma-js/src/utils/distance.js
  function distance_default(a, b, mode = "lab") {
    a = new Color_default(a);
    b = new Color_default(b);
    const l1 = a.get(mode);
    const l2 = b.get(mode);
    let sum_sq = 0;
    for (let i in l1) {
      const d = (l1[i] || 0) - (l2[i] || 0);
      sum_sq += d * d;
    }
    return Math.sqrt(sum_sq);
  }

  // node_modules/chroma-js/src/utils/valid.js
  var valid_default = (...args) => {
    try {
      new Color_default(...args);
      return true;
    } catch (e) {
      return false;
    }
  };

  // node_modules/chroma-js/src/utils/scales.js
  var scales_default = {
    cool() {
      return scale_default([chroma_default.hsl(180, 1, 0.9), chroma_default.hsl(250, 0.7, 0.4)]);
    },
    hot() {
      return scale_default(["#000", "#f00", "#ff0", "#fff"], [0, 0.25, 0.75, 1]).mode(
        "rgb"
      );
    }
  };

  // node_modules/chroma-js/src/colors/colorbrewer.js
  var colorbrewer = {
    // sequential
    OrRd: ["#fff7ec", "#fee8c8", "#fdd49e", "#fdbb84", "#fc8d59", "#ef6548", "#d7301f", "#b30000", "#7f0000"],
    PuBu: ["#fff7fb", "#ece7f2", "#d0d1e6", "#a6bddb", "#74a9cf", "#3690c0", "#0570b0", "#045a8d", "#023858"],
    BuPu: ["#f7fcfd", "#e0ecf4", "#bfd3e6", "#9ebcda", "#8c96c6", "#8c6bb1", "#88419d", "#810f7c", "#4d004b"],
    Oranges: ["#fff5eb", "#fee6ce", "#fdd0a2", "#fdae6b", "#fd8d3c", "#f16913", "#d94801", "#a63603", "#7f2704"],
    BuGn: ["#f7fcfd", "#e5f5f9", "#ccece6", "#99d8c9", "#66c2a4", "#41ae76", "#238b45", "#006d2c", "#00441b"],
    YlOrBr: ["#ffffe5", "#fff7bc", "#fee391", "#fec44f", "#fe9929", "#ec7014", "#cc4c02", "#993404", "#662506"],
    YlGn: ["#ffffe5", "#f7fcb9", "#d9f0a3", "#addd8e", "#78c679", "#41ab5d", "#238443", "#006837", "#004529"],
    Reds: ["#fff5f0", "#fee0d2", "#fcbba1", "#fc9272", "#fb6a4a", "#ef3b2c", "#cb181d", "#a50f15", "#67000d"],
    RdPu: ["#fff7f3", "#fde0dd", "#fcc5c0", "#fa9fb5", "#f768a1", "#dd3497", "#ae017e", "#7a0177", "#49006a"],
    Greens: ["#f7fcf5", "#e5f5e0", "#c7e9c0", "#a1d99b", "#74c476", "#41ab5d", "#238b45", "#006d2c", "#00441b"],
    YlGnBu: ["#ffffd9", "#edf8b1", "#c7e9b4", "#7fcdbb", "#41b6c4", "#1d91c0", "#225ea8", "#253494", "#081d58"],
    Purples: ["#fcfbfd", "#efedf5", "#dadaeb", "#bcbddc", "#9e9ac8", "#807dba", "#6a51a3", "#54278f", "#3f007d"],
    GnBu: ["#f7fcf0", "#e0f3db", "#ccebc5", "#a8ddb5", "#7bccc4", "#4eb3d3", "#2b8cbe", "#0868ac", "#084081"],
    Greys: ["#ffffff", "#f0f0f0", "#d9d9d9", "#bdbdbd", "#969696", "#737373", "#525252", "#252525", "#000000"],
    YlOrRd: ["#ffffcc", "#ffeda0", "#fed976", "#feb24c", "#fd8d3c", "#fc4e2a", "#e31a1c", "#bd0026", "#800026"],
    PuRd: ["#f7f4f9", "#e7e1ef", "#d4b9da", "#c994c7", "#df65b0", "#e7298a", "#ce1256", "#980043", "#67001f"],
    Blues: ["#f7fbff", "#deebf7", "#c6dbef", "#9ecae1", "#6baed6", "#4292c6", "#2171b5", "#08519c", "#08306b"],
    PuBuGn: ["#fff7fb", "#ece2f0", "#d0d1e6", "#a6bddb", "#67a9cf", "#3690c0", "#02818a", "#016c59", "#014636"],
    Viridis: ["#440154", "#482777", "#3f4a8a", "#31678e", "#26838f", "#1f9d8a", "#6cce5a", "#b6de2b", "#fee825"],
    // diverging
    Spectral: ["#9e0142", "#d53e4f", "#f46d43", "#fdae61", "#fee08b", "#ffffbf", "#e6f598", "#abdda4", "#66c2a5", "#3288bd", "#5e4fa2"],
    RdYlGn: ["#a50026", "#d73027", "#f46d43", "#fdae61", "#fee08b", "#ffffbf", "#d9ef8b", "#a6d96a", "#66bd63", "#1a9850", "#006837"],
    RdBu: ["#67001f", "#b2182b", "#d6604d", "#f4a582", "#fddbc7", "#f7f7f7", "#d1e5f0", "#92c5de", "#4393c3", "#2166ac", "#053061"],
    PiYG: ["#8e0152", "#c51b7d", "#de77ae", "#f1b6da", "#fde0ef", "#f7f7f7", "#e6f5d0", "#b8e186", "#7fbc41", "#4d9221", "#276419"],
    PRGn: ["#40004b", "#762a83", "#9970ab", "#c2a5cf", "#e7d4e8", "#f7f7f7", "#d9f0d3", "#a6dba0", "#5aae61", "#1b7837", "#00441b"],
    RdYlBu: ["#a50026", "#d73027", "#f46d43", "#fdae61", "#fee090", "#ffffbf", "#e0f3f8", "#abd9e9", "#74add1", "#4575b4", "#313695"],
    BrBG: ["#543005", "#8c510a", "#bf812d", "#dfc27d", "#f6e8c3", "#f5f5f5", "#c7eae5", "#80cdc1", "#35978f", "#01665e", "#003c30"],
    RdGy: ["#67001f", "#b2182b", "#d6604d", "#f4a582", "#fddbc7", "#ffffff", "#e0e0e0", "#bababa", "#878787", "#4d4d4d", "#1a1a1a"],
    PuOr: ["#7f3b08", "#b35806", "#e08214", "#fdb863", "#fee0b6", "#f7f7f7", "#d8daeb", "#b2abd2", "#8073ac", "#542788", "#2d004b"],
    // qualitative
    Set2: ["#66c2a5", "#fc8d62", "#8da0cb", "#e78ac3", "#a6d854", "#ffd92f", "#e5c494", "#b3b3b3"],
    Accent: ["#7fc97f", "#beaed4", "#fdc086", "#ffff99", "#386cb0", "#f0027f", "#bf5b17", "#666666"],
    Set1: ["#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00", "#ffff33", "#a65628", "#f781bf", "#999999"],
    Set3: ["#8dd3c7", "#ffffb3", "#bebada", "#fb8072", "#80b1d3", "#fdb462", "#b3de69", "#fccde5", "#d9d9d9", "#bc80bd", "#ccebc5", "#ffed6f"],
    Dark2: ["#1b9e77", "#d95f02", "#7570b3", "#e7298a", "#66a61e", "#e6ab02", "#a6761d", "#666666"],
    Paired: ["#a6cee3", "#1f78b4", "#b2df8a", "#33a02c", "#fb9a99", "#e31a1c", "#fdbf6f", "#ff7f00", "#cab2d6", "#6a3d9a", "#ffff99", "#b15928"],
    Pastel2: ["#b3e2cd", "#fdcdac", "#cbd5e8", "#f4cae4", "#e6f5c9", "#fff2ae", "#f1e2cc", "#cccccc"],
    Pastel1: ["#fbb4ae", "#b3cde3", "#ccebc5", "#decbe4", "#fed9a6", "#ffffcc", "#e5d8bd", "#fddaec", "#f2f2f2"]
  };
  for (let key of Object.keys(colorbrewer)) {
    colorbrewer[key.toLowerCase()] = colorbrewer[key];
  }
  var colorbrewer_default = colorbrewer;

  // node_modules/chroma-js/index.js
  Object.assign(chroma_default, {
    average: average_default,
    bezier: bezier_default,
    blend: blend_default,
    cubehelix: cubehelix_default,
    mix: mix_default,
    interpolate: mix_default,
    random: random_default,
    scale: scale_default,
    analyze,
    contrast: contrast_default,
    deltaE: delta_e_default,
    distance: distance_default,
    limits,
    valid: valid_default,
    scales: scales_default,
    input: input_default,
    colors: w3cx11_default,
    brewer: colorbrewer_default
  });
  var chroma_js_default = chroma_default;

  // node_modules/smiles-drawer/src/GaussDrawer.js
  var GaussDrawer = class {
    /**
     * The constructor of the class Graph.
     *
     * @param {Vector2[]} points The centres of the gaussians.
     * @param {Number[]} weights The weights / amplitudes for each gaussian.
     */
    constructor(points, weights, width, height, sigma = 0.3, interval = 0, colormap = null, opacity = 1, normalized = false) {
      this.points = points;
      this.weights = weights;
      this.width = width;
      this.height = height;
      this.sigma = sigma;
      this.interval = interval;
      this.opacity = opacity;
      this.normalized = normalized;
      if (colormap === null) {
        let piyg11 = [
          "#c51b7d",
          "#de77ae",
          "#f1b6da",
          "#fde0ef",
          "#ffffff",
          "#e6f5d0",
          "#b8e186",
          "#7fbc41",
          "#4d9221"
        ];
        colormap = piyg11;
      }
      this.colormap = colormap;
      this.canvas = document.createElement("canvas");
      this.context = this.canvas.getContext("2d");
      this.canvas.width = this.width;
      this.canvas.height = this.height;
    }
    setFromArray(arr_points, arr_weights) {
      this.points = [];
      arr_points.forEach((a) => {
        this.points.push(new Vector2(a[0], a[1]));
      });
      this.weights = [];
      arr_weights.forEach((w) => {
        this.weights.push(w);
      });
    }
    /**
       * Compute and draw the gaussians.
       */
    draw() {
      let m = [];
      for (let x = 0; x < this.width; x++) {
        let row = [];
        for (let y = 0; y < this.height; y++) {
          row.push(0);
        }
        m.push(row);
      }
      let divisor = 1 / (2 * this.sigma * this.sigma);
      for (let i = 0; i < this.points.length; i++) {
        let v = this.points[i];
        let a = this.weights[i];
        for (let x = 0; x < this.width; x++) {
          for (let y = 0; y < this.height; y++) {
            let dx = x - v.x;
            let dy = y - v.y;
            let v_xy = (dx * dx + dy * dy) * divisor;
            let val = a * Math.exp(-v_xy);
            m[x][y] += val;
          }
        }
      }
      let abs_max = 1;
      if (!this.normalized) {
        let max5 = -Number.MAX_SAFE_INTEGER;
        let min5 = Number.MAX_SAFE_INTEGER;
        for (let x = 0; x < this.width; x++) {
          for (let y = 0; y < this.height; y++) {
            if (m[x][y] < min5) {
              min5 = m[x][y];
            }
            if (m[x][y] > max5) {
              max5 = m[x][y];
            }
          }
        }
        abs_max = Math.max(Math.abs(min5), Math.abs(max5));
      }
      const scale = chroma_js_default.scale(this.colormap).domain([-1, 1]);
      for (let x = 0; x < this.width; x++) {
        for (let y = 0; y < this.height; y++) {
          if (!this.normalized) {
            m[x][y] = m[x][y] / abs_max;
          }
          if (this.interval !== 0) {
            m[x][y] = Math.round(m[x][y] / this.interval) * this.interval;
          }
          let [r, g, b] = scale(m[x][y]).rgb();
          this.setPixel(new Vector2(x, y), r, g, b);
        }
      }
    }
    /**
       * Get the canvas as an HTML image.
       *
       * @param {CallableFunction} callback
       */
    getImage(callback) {
      let image = new Image();
      image.onload = () => {
        this.context.imageSmoothingEnabled = false;
        this.context.drawImage(image, 0, 0, this.width, this.height);
        if (callback) {
          callback(image);
        }
      };
      image.onerror = (err) => {
        console.log(err);
      };
      image.src = this.canvas.toDataURL();
    }
    /**
       * Get the canvas as an SVG element.
       */
    getSVG() {
      return convertImage(this.context.getImageData(0, 0, this.width, this.height));
    }
    /**
       * Set the colour at a specific point on the canvas.
       *
       * @param {Vector2} vec The pixel position on the canvas.
       * @param {Number} r The red colour-component.
       * @param {Number} g The green colour-component.
       * @param {Number} b The blue colour-component.
       */
    setPixel(vec, r, g, b) {
      this.context.fillStyle = "rgba(" + r + "," + g + "," + b + "," + this.opacity + ")";
      this.context.fillRect(vec.x, vec.y, 1, 1);
    }
  };

  // node_modules/smiles-drawer/src/SvgWrapper.js
  function makeid(length) {
    let result = "";
    let characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    let charactersLength = characters.length;
    for (let i = 0; i < length; i++) {
      result += characters.charAt(Math.floor(Math.random() * charactersLength));
    }
    return result;
  }
  var SvgWrapper = class _SvgWrapper {
    constructor(themeManager, target, options, clear = true) {
      if (typeof target === "string" || target instanceof String) {
        this.svg = document.getElementById(target);
      } else {
        this.svg = target;
      }
      this.container = null;
      this.opts = options;
      this.uid = makeid(5);
      this.gradientId = 0;
      this.backgroundItems = [];
      this.paths = [];
      this.vertices = [];
      this.gradients = [];
      this.highlights = [];
      this.drawingWidth = 0;
      this.drawingHeight = 0;
      this.halfBondThickness = this.opts.bondThickness / 2;
      this.themeManager = themeManager;
      this.maskElements = [];
      this.maxX = -Number.MAX_VALUE;
      this.maxY = -Number.MAX_VALUE;
      this.minX = Number.MAX_VALUE;
      this.minY = Number.MAX_VALUE;
      if (clear) {
        while (this.svg.firstChild) {
          this.svg.removeChild(this.svg.firstChild);
        }
      }
      this.style = document.createElementNS("http://www.w3.org/2000/svg", "style");
      this.style.appendChild(document.createTextNode(`
                .element {
                    font: ${this.opts.fontSizeLarge}pt ${this.opts.fontFamily};
                }
                .sub {
                    font: ${this.opts.fontSizeSmall}pt ${this.opts.fontFamily};
                }
            `));
      if (this.svg) {
        this.svg.appendChild(this.style);
      } else {
        this.container = document.createElementNS("http://www.w3.org/2000/svg", "g");
        this.container.appendChild(this.style);
      }
    }
    constructSvg() {
      let defs = document.createElementNS("http://www.w3.org/2000/svg", "defs"), masks = document.createElementNS("http://www.w3.org/2000/svg", "mask"), background = document.createElementNS("http://www.w3.org/2000/svg", "g"), highlights = document.createElementNS("http://www.w3.org/2000/svg", "g"), paths = document.createElementNS("http://www.w3.org/2000/svg", "g"), vertices = document.createElementNS("http://www.w3.org/2000/svg", "g"), pathChildNodes = this.paths;
      {
        let mask = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        mask.setAttributeNS(null, "x", this.minX);
        mask.setAttributeNS(null, "y", this.minY);
        mask.setAttributeNS(null, "width", this.maxX - this.minX);
        mask.setAttributeNS(null, "height", this.maxY - this.minY);
        mask.setAttributeNS(null, "fill", "white");
        masks.appendChild(mask);
      }
      masks.setAttributeNS(null, "id", this.uid + "-text-mask");
      masks.setAttributeNS(null, "maskUnits", "userSpaceOnUse");
      masks.setAttributeNS(null, "x", this.minX);
      masks.setAttributeNS(null, "y", this.minY);
      masks.setAttributeNS(null, "width", this.maxX - this.minX);
      masks.setAttributeNS(null, "height", this.maxY - this.minY);
      for (let path of pathChildNodes) {
        paths.appendChild(path);
      }
      for (let backgroundItem of this.backgroundItems) {
        background.appendChild(backgroundItem);
      }
      for (let highlight of this.highlights) {
        highlights.appendChild(highlight);
      }
      for (let vertex of this.vertices) {
        vertices.appendChild(vertex);
      }
      for (let mask of this.maskElements) {
        masks.appendChild(mask);
      }
      for (let gradient of this.gradients) {
        defs.appendChild(gradient);
      }
      paths.setAttributeNS(null, "mask", "url(#" + this.uid + "-text-mask)");
      this.updateViewbox(this.opts.scale);
      background.setAttributeNS(null, "style", `transform: translateX(${this.minX}px) translateY(${this.minY}px)`);
      if (this.svg) {
        this.svg.appendChild(defs);
        this.svg.appendChild(masks);
        this.svg.appendChild(background);
        this.svg.appendChild(highlights);
        this.svg.appendChild(paths);
        this.svg.appendChild(vertices);
      } else {
        this.container.appendChild(defs);
        this.container.appendChild(masks);
        this.container.appendChild(background);
        this.container.appendChild(paths);
        this.container.appendChild(vertices);
        return this.container;
      }
    }
    /**
     * Add a background to the svg.
     */
    addLayer(svg) {
      this.backgroundItems.push(svg.firstChild);
    }
    /**
     * Create a linear gradient to apply to a line
     *
     * @param {Line} line the line to apply the gradiation to.
     */
    createGradient(line) {
      let gradient = document.createElementNS("http://www.w3.org/2000/svg", "linearGradient"), gradientUrl = this.uid + `-line-${this.gradientId++}`, l = line.getLeftVector(), r = line.getRightVector(), fromX = l.x, fromY = l.y, toX = r.x, toY = r.y;
      gradient.setAttributeNS(null, "id", gradientUrl);
      gradient.setAttributeNS(null, "gradientUnits", "userSpaceOnUse");
      gradient.setAttributeNS(null, "x1", fromX);
      gradient.setAttributeNS(null, "y1", fromY);
      gradient.setAttributeNS(null, "x2", toX);
      gradient.setAttributeNS(null, "y2", toY);
      let firstStop = document.createElementNS("http://www.w3.org/2000/svg", "stop");
      firstStop.setAttributeNS(null, "stop-color", this.themeManager.getColor(line.getLeftElement()) || this.themeManager.getColor("C"));
      firstStop.setAttributeNS(null, "offset", "20%");
      let secondStop = document.createElementNS("http://www.w3.org/2000/svg", "stop");
      secondStop.setAttributeNS(null, "stop-color", this.themeManager.getColor(line.getRightElement() || this.themeManager.getColor("C")));
      secondStop.setAttributeNS(null, "offset", "100%");
      gradient.appendChild(firstStop);
      gradient.appendChild(secondStop);
      this.gradients.push(gradient);
      return gradientUrl;
    }
    /**
     * Create a tspan element for sub or super scripts that styles the text
     * appropriately as one of those text types.
     *
     * @param {String} text the actual text
     * @param {String} shift the type of text, either 'sub', or 'super'
     */
    createSubSuperScripts(text, shift) {
      let elem = document.createElementNS("http://www.w3.org/2000/svg", "tspan");
      elem.setAttributeNS(null, "baseline-shift", shift);
      elem.appendChild(document.createTextNode(text));
      elem.setAttributeNS(null, "class", "sub");
      return elem;
    }
    static createUnicodeCharge(n) {
      if (n === 1) {
        return "\u207A";
      }
      if (n === -1) {
        return "\u207B";
      }
      if (n > 1) {
        return _SvgWrapper.createUnicodeSuperscript(n) + "\u207A";
      }
      if (n < -1) {
        return _SvgWrapper.createUnicodeSuperscript(n) + "\u207B";
      }
      return "";
    }
    /**
     * Determine drawing dimensiosn based on vertex positions.
     *
     * @param {Vertex[]} vertices An array of vertices containing the vertices associated with the current molecule.
     */
    determineDimensions(vertices) {
      for (let i = 0; i < vertices.length; i++) {
        if (!vertices[i].value.isDrawn) {
          continue;
        }
        let p = vertices[i].position;
        if (this.maxX < p.x) this.maxX = p.x;
        if (this.maxY < p.y) this.maxY = p.y;
        if (this.minX > p.x) this.minX = p.x;
        if (this.minY > p.y) this.minY = p.y;
      }
      let padding = this.opts.padding;
      this.maxX += padding;
      this.maxY += padding;
      this.minX -= padding;
      this.minY -= padding;
      this.drawingWidth = this.maxX - this.minX;
      this.drawingHeight = this.maxY - this.minY;
    }
    updateViewbox(scale) {
      let x = this.minX;
      let y = this.minY;
      let width = this.maxX - this.minX;
      let height = this.maxY - this.minY;
      if (scale <= 0) {
        if (width > height) {
          let diff = width - height;
          height = width;
          y -= diff / 2;
        } else {
          let diff = height - width;
          width = height;
          x -= diff / 2;
        }
      } else {
        if (this.svg) {
          this.svg.style.width = scale * width + "px";
          this.svg.style.height = scale * height + "px";
        }
      }
      this.svg.setAttributeNS(null, "viewBox", `${x} ${y} ${width} ${height}`);
    }
    /**
     * Draw an svg ellipse as a ball.
     *
     * @param {Number} x The x position of the text.
     * @param {Number} y The y position of the text.
     * @param {String} elementName The name of the element (single-letter).
     */
    drawBall(x, y, elementName) {
      let r = this.opts.bondLength / 4.5;
      if (x - r < this.minX) {
        this.minX = x - r;
      }
      if (x + r > this.maxX) {
        this.maxX = x + r;
      }
      if (y - r < this.minY) {
        this.minY = y - r;
      }
      if (y + r > this.maxY) {
        this.maxY = y + r;
      }
      let ball = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      ball.setAttributeNS(null, "cx", x);
      ball.setAttributeNS(null, "cy", y);
      ball.setAttributeNS(null, "r", r);
      ball.setAttributeNS(null, "fill", this.themeManager.getColor(elementName));
      this.vertices.push(ball);
    }
    /**
     * @param {Line} line the line object to create the wedge from
     */
    drawWedge(line) {
      let l = line.getLeftVector().clone(), r = line.getRightVector().clone();
      let normals = Vector2.normals(l, r);
      normals[0].normalize();
      normals[1].normalize();
      let isRightChiralCenter = line.getRightChiral();
      let start = l, end = r;
      if (isRightChiralCenter) {
        start = r;
        end = l;
      }
      let t = Vector2.add(start, Vector2.multiplyScalar(normals[0], this.halfBondThickness)), u = Vector2.add(end, Vector2.multiplyScalar(normals[0], 3 + this.opts.fontSizeLarge / 4)), v = Vector2.add(end, Vector2.multiplyScalar(normals[1], 3 + this.opts.fontSizeLarge / 4)), w = Vector2.add(start, Vector2.multiplyScalar(normals[1], this.halfBondThickness));
      let polygon = document.createElementNS("http://www.w3.org/2000/svg", "polygon"), gradient = this.createGradient(line, l.x, l.y, r.x, r.y);
      polygon.setAttributeNS(null, "points", `${t.x},${t.y} ${u.x},${u.y} ${v.x},${v.y} ${w.x},${w.y}`);
      polygon.setAttributeNS(null, "fill", `url('#${gradient}')`);
      this.paths.push(polygon);
    }
    /* Draw a highlight for an atom
     *
     *  @param {Number} x The x position of the highlight
     *  @param {Number} y The y position of the highlight
     *  @param {string} color The color of the highlight, default #03fc9d
     */
    drawAtomHighlight(x, y, color = "#03fc9d") {
      let ball = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      ball.setAttributeNS(null, "cx", x);
      ball.setAttributeNS(null, "cy", y);
      ball.setAttributeNS(null, "r", this.opts.bondLength / 3);
      ball.setAttributeNS(null, "fill", color);
      this.highlights.push(ball);
    }
    /**
     * Draw a dashed wedge on the canvas.
     *
     * @param {Line} line A line.
     */
    drawDashedWedge(line) {
      if (isNaN(line.from.x) || isNaN(line.from.y) || isNaN(line.to.x) || isNaN(line.to.y)) {
        return;
      }
      let l = line.getLeftVector().clone(), r = line.getRightVector().clone(), normals = Vector2.normals(l, r);
      normals[0].normalize();
      normals[1].normalize();
      let isRightChiralCenter = line.getRightChiral(), start, end;
      if (isRightChiralCenter) {
        start = r;
        end = l;
      } else {
        start = l;
        end = r;
      }
      let dir = Vector2.subtract(end, start).normalize(), length = line.getLength(), step = 1.25 / (length / (this.opts.bondLength / 10));
      let gradient = this.createGradient(line);
      for (let t = 0; t < 1; t += step) {
        let to = Vector2.multiplyScalar(dir, t * length), startDash = Vector2.add(start, to), width = this.opts.fontSizeLarge / 2 * t, dashOffset = Vector2.multiplyScalar(normals[0], width);
        startDash.subtract(dashOffset);
        let endDash = startDash.clone();
        endDash.add(Vector2.multiplyScalar(dashOffset, 2));
        this.drawLine(new Line(startDash, endDash), null, gradient);
      }
    }
    /**
     * Draws a debug dot at a given coordinate and adds text.
     *
     * @param {Number} x The x coordinate.
     * @param {Number} y The y coordindate.
     * @param {String} [debugText=''] A string.
     * @param {String} [color='#f00'] A color in hex form.
     */
    drawDebugPoint(x, y, debugText = "", color = "#f00") {
      let point = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      point.setAttributeNS(null, "cx", x);
      point.setAttributeNS(null, "cy", y);
      point.setAttributeNS(null, "r", "2");
      point.setAttributeNS(null, "fill", color);
      this.vertices.push(point);
      this.drawDebugText(x, y, debugText);
    }
    /**
     * Draws a debug text message at a given position
     *
     * @param {Number} x The x coordinate.
     * @param {Number} y The y coordinate.
     * @param {String} text The debug text.
     */
    drawDebugText(x, y, text) {
      let textElem = document.createElementNS("http://www.w3.org/2000/svg", "text");
      textElem.setAttributeNS(null, "x", x);
      textElem.setAttributeNS(null, "y", y);
      textElem.setAttributeNS(null, "class", "debug");
      textElem.setAttributeNS(null, "fill", "#ff0000");
      textElem.setAttributeNS(null, "style", `
                font: 5px Droid Sans, sans-serif;
            `);
      textElem.appendChild(document.createTextNode(text));
      this.vertices.push(textElem);
    }
    /**
     * Draws a ring.
     *
     * @param {x} x The x coordinate of the ring.
     * @param {y} r The y coordinate of the ring.
     * @param {s} s The size of the ring.
     */
    drawRing(x, y, s) {
      let circleElem = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      let radius = MathHelper.apothemFromSideLength(this.opts.bondLength, s);
      circleElem.setAttributeNS(null, "cx", x);
      circleElem.setAttributeNS(null, "cy", y);
      circleElem.setAttributeNS(null, "r", radius - this.opts.bondSpacing);
      circleElem.setAttributeNS(null, "stroke", this.themeManager.getColor("C"));
      circleElem.setAttributeNS(null, "stroke-width", this.opts.bondThickness);
      circleElem.setAttributeNS(null, "fill", "none");
      this.paths.push(circleElem);
    }
    /**
     * Draws a line.
     *
     * @param {Line} line A line.
     * @param {Boolean} dashed defaults to false.
     * @param {String} gradient gradient url. Defaults to null.
     */
    drawLine(line, dashed = false, gradient = null, linecap = "round") {
      let stylesArr = [
        ["stroke-width", this.opts.bondThickness],
        ["stroke-linecap", linecap],
        ["stroke-dasharray", dashed ? "5, 5" : "none"]
      ], l = line.getLeftVector(), r = line.getRightVector(), fromX = l.x, fromY = l.y, toX = r.x, toY = r.y;
      let styles = stylesArr.map((sub) => sub.join(":")).join(";"), lineElem = document.createElementNS("http://www.w3.org/2000/svg", "line");
      lineElem.setAttributeNS(null, "x1", fromX);
      lineElem.setAttributeNS(null, "y1", fromY);
      lineElem.setAttributeNS(null, "x2", toX);
      lineElem.setAttributeNS(null, "y2", toY);
      lineElem.setAttributeNS(null, "style", styles);
      this.paths.push(lineElem);
      if (gradient == null) {
        gradient = this.createGradient(line, fromX, fromY, toX, toY);
      }
      lineElem.setAttributeNS(null, "stroke", `url('#${gradient}')`);
    }
    /**
     * Draw a point.
     *
     * @param {Number} x The x position of the point.
     * @param {Number} y The y position of the point.
     * @param {String} elementName The name of the element (single-letter).
     */
    drawPoint(x, y, elementName) {
      let r = 0.75;
      if (x - r < this.minX) {
        this.minX = x - r;
      }
      if (x + r > this.maxX) {
        this.maxX = x + r;
      }
      if (y - r < this.minY) {
        this.minY = y - r;
      }
      if (y + r > this.maxY) {
        this.maxY = y + r;
      }
      let mask = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      mask.setAttributeNS(null, "cx", x);
      mask.setAttributeNS(null, "cy", y);
      mask.setAttributeNS(null, "r", "1.5");
      mask.setAttributeNS(null, "fill", "black");
      this.maskElements.push(mask);
      let point = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      point.setAttributeNS(null, "cx", x);
      point.setAttributeNS(null, "cy", y);
      point.setAttributeNS(null, "r", r);
      point.setAttributeNS(null, "fill", this.themeManager.getColor(elementName));
      this.vertices.push(point);
    }
    /**
     * Draw a text to the canvas.
     *
     * @param {Number} x The x position of the text.
     * @param {Number} y The y position of the text.
     * @param {String} elementName The name of the element (single-letter).
     * @param {Number} hydrogens The number of hydrogen atoms.
     * @param {String} direction The direction of the text in relation to the associated vertex.
     * @param {Boolean} isTerminal A boolean indicating whether or not the vertex is terminal.
     * @param {Number} charge The charge of the atom.
     * @param {Number} isotope The isotope number.
     * @param {Number} totalVertices The total number of vertices in the graph.
     * @param {Object} attachedPseudoElement A map with containing information for pseudo elements or concatinated elements. The key is comprised of the element symbol and the hydrogen count.
     * @param {String} attachedPseudoElement.element The element symbol.
     * @param {Number} attachedPseudoElement.count The number of occurences that match the key.
     * @param {Number} attachedPseudoElement.hyrogenCount The number of hydrogens attached to each atom matching the key.
     */
    drawText(x, y, elementName, hydrogens, direction, isTerminal, charge, isotope, totalVertices, attachedPseudoElement = {}) {
      let text = [];
      let display = elementName;
      if (charge !== 0 && charge !== null) {
        display += _SvgWrapper.createUnicodeCharge(charge);
      }
      if (isotope !== 0 && isotope !== null) {
        display = _SvgWrapper.createUnicodeSuperscript(isotope) + display;
      }
      text.push([display, elementName]);
      if (hydrogens === 1) {
        text.push(["H", "H"]);
      } else if (hydrogens > 1) {
        text.push(["H" + _SvgWrapper.createUnicodeSubscript(hydrogens), "H"]);
      }
      if (charge === 1 && elementName === "N" && "0O" in attachedPseudoElement && "0O-1" in attachedPseudoElement) {
        attachedPseudoElement = { "0O": { element: "O", count: 2, hydrogenCount: 0, previousElement: "C", charge: "" } };
        charge = 0;
      }
      for (let key of Object.keys(attachedPseudoElement)) {
        let pe = attachedPseudoElement[key];
        let pe_display = pe.element;
        if (pe.count > 1) {
          pe_display += _SvgWrapper.createUnicodeSubscript(pe.count);
        }
        if (pe.charge) {
          pe_display += _SvgWrapper.createUnicodeCharge(pe.charge);
        }
        text.push([pe_display, pe.element]);
        if (pe.hydrogenCount === 1) {
          text.push(["H", "H"]);
        } else if (pe.hydrogenCount > 1) {
          text.push(["H" + _SvgWrapper.createUnicodeSubscript(pe.hydrogenCount), "H"]);
        }
      }
      this.write(text, direction, x, y, totalVertices === 1);
    }
    write(text, direction, x, y, singleVertex) {
      let bbox = _SvgWrapper.measureText(text[0][1], this.opts.fontSizeLarge, this.opts.fontFamily);
      if (direction === "left" && text[0][0] !== text[0][1]) {
        let fullBbox = _SvgWrapper.measureText(text[0][0], this.opts.fontSizeLarge, this.opts.fontFamily);
        bbox.width = fullBbox.width;
      }
      if (singleVertex) {
        if (x + bbox.width * text.length > this.maxX) {
          this.maxX = x + bbox.width * text.length;
        }
        if (x - bbox.width / 2 < this.minX) {
          this.minX = x - bbox.width / 2;
        }
        if (y - bbox.height < this.minY) {
          this.minY = y - bbox.height;
        }
        if (y + bbox.height > this.maxY) {
          this.maxY = y + bbox.height;
        }
      } else {
        if (direction !== "right") {
          if (x + bbox.width * text.length > this.maxX) {
            this.maxX = x + bbox.width * text.length;
          }
          if (x - bbox.width * text.length < this.minX) {
            this.minX = x - bbox.width * text.length;
          }
        } else if (direction !== "left") {
          if (x + bbox.width * text.length > this.maxX) {
            this.maxX = x + bbox.width * text.length;
          }
          if (x - bbox.width / 2 < this.minX) {
            this.minX = x - bbox.width / 2;
          }
        }
        if (y - bbox.height < this.minY) {
          this.minY = y - bbox.height;
        }
        if (y + bbox.height > this.maxY) {
          this.maxY = y + bbox.height;
        }
        if (direction === "down") {
          if (y + 0.8 * bbox.height * text.length > this.maxY) {
            this.maxY = y + 0.8 * bbox.height * text.length;
          }
        }
        if (direction === "up") {
          if (y - 0.8 * bbox.height * text.length < this.minY) {
            this.minY = y - 0.8 * bbox.height * text.length;
          }
        }
      }
      let cx = x;
      let cy = y;
      let textElem = document.createElementNS("http://www.w3.org/2000/svg", "text");
      textElem.setAttributeNS(null, "class", "element");
      let g = document.createElementNS("http://www.w3.org/2000/svg", "g");
      textElem.setAttributeNS(null, "fill", "#ffffff");
      if (direction === "left") {
        text = text.reverse();
      }
      if (direction === "right" || direction === "down" || direction === "up") {
        x -= bbox.width / 2;
      }
      if (direction === "left") {
        x += bbox.width / 2;
      }
      text.forEach((part, i) => {
        const display = part[0];
        const elementName = part[1];
        let tspanElem = document.createElementNS("http://www.w3.org/2000/svg", "tspan");
        tspanElem.setAttributeNS(null, "fill", this.themeManager.getColor(elementName));
        tspanElem.textContent = display;
        if (direction === "up" || direction === "down") {
          tspanElem.setAttributeNS(null, "x", "0px");
          if (direction === "up") {
            tspanElem.setAttributeNS(null, "y", `-${0.9 * i}em`);
          } else {
            tspanElem.setAttributeNS(null, "y", `${0.9 * i}em`);
          }
        }
        textElem.appendChild(tspanElem);
      });
      textElem.setAttributeNS(null, "data-direction", direction);
      if (direction === "left" || direction === "right") {
        textElem.setAttributeNS(null, "dominant-baseline", "alphabetic");
        textElem.setAttributeNS(null, "y", "0.36em");
      } else {
        textElem.setAttributeNS(null, "dominant-baseline", "central");
      }
      if (direction === "left") {
        textElem.setAttributeNS(null, "text-anchor", "end");
      }
      g.appendChild(textElem);
      g.setAttributeNS(null, "style", `transform: translateX(${x}px) translateY(${y}px)`);
      let maskRadius = this.opts.fontSizeLarge * 0.75;
      if (text[0][1].length > 1) {
        maskRadius = this.opts.fontSizeLarge * 1.1;
      }
      let mask = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      mask.setAttributeNS(null, "cx", cx);
      mask.setAttributeNS(null, "cy", cy);
      mask.setAttributeNS(null, "r", maskRadius);
      mask.setAttributeNS(null, "fill", "black");
      this.maskElements.push(mask);
      this.vertices.push(g);
    }
    /**
     * Draw the wrapped SVG to a canvas.
     * @param {HTMLCanvasElement} canvas The canvas element to draw the svg to.
     */
    toCanvas(canvas, width, height) {
      if (typeof canvas === "string" || canvas instanceof String) {
        canvas = document.getElementById(canvas);
      }
      let image = new Image();
      image.onload = function() {
        canvas.width = width;
        canvas.height = height;
        canvas.getContext("2d").drawImage(image, 0, 0, width, height);
      };
      image.src = "data:image/svg+xml;charset-utf-8," + encodeURIComponent(this.svg.outerHTML);
    }
    static createUnicodeSubscript(n) {
      let result = "";
      n.toString().split("").forEach((d) => {
        result += ["\u2080", "\u2081", "\u2082", "\u2083", "\u2084", "\u2085", "\u2086", "\u2087", "\u2088", "\u2089"][parseInt(d)];
      });
      return result;
    }
    static createUnicodeSuperscript(n) {
      let result = "";
      n.toString().split("").forEach((d) => {
        let parsed = parseInt(d);
        if (Number.isFinite(parsed)) {
          result += ["\u2070", "\xB9", "\xB2", "\xB3", "\u2074", "\u2075", "\u2076", "\u2077", "\u2078", "\u2079"][parsed];
        }
      });
      return result;
    }
    static replaceNumbersWithSubscript(text) {
      let subscriptNumbers = { 0: "\u2080", 1: "\u2081", 2: "\u2082", 3: "\u2083", 4: "\u2084", 5: "\u2085", 6: "\u2086", 7: "\u2087", 8: "\u2088", 9: "\u2089" };
      for (const [key, value] of Object.entries(subscriptNumbers)) {
        text = text.replaceAll(key, value);
      }
      return text;
    }
    static measureText(text, fontSize, fontFamily, lineHeight = 0.9) {
      const element = document.createElement("canvas");
      const ctx = element.getContext("2d");
      ctx.font = `${fontSize}pt ${fontFamily}`;
      let textMetrics = ctx.measureText(text);
      let compWidth = Math.abs(textMetrics.actualBoundingBoxLeft) + Math.abs(textMetrics.actualBoundingBoxRight);
      return {
        width: textMetrics.width > compWidth ? textMetrics.width : compWidth,
        height: (Math.abs(textMetrics.actualBoundingBoxAscent) + Math.abs(textMetrics.actualBoundingBoxAscent)) * lineHeight
      };
    }
    /**
     * Convert an SVG to a canvas. Warning: This happens async!
     *
     * @param {SVGElement} svg
     * @param {HTMLCanvasElement} canvas
     * @param {Number} width
     * @param {Number} height
     * @param {CallableFunction} callback
     * @returns {HTMLCanvasElement} The input html canvas element after drawing to.
     */
    static svgToCanvas(svg, canvas, width, height, callback = null) {
      svg.setAttributeNS(null, "width", width);
      svg.setAttributeNS(null, "height", height);
      let image = new Image();
      image.onload = function() {
        canvas.width = width;
        canvas.height = height;
        let context = canvas.getContext("2d");
        context.imageSmoothingEnabled = false;
        context.drawImage(image, 0, 0, width, height);
        if (callback) {
          callback(canvas);
        }
      };
      image.onerror = function(err) {
        console.log(err);
      };
      image.src = "data:image/svg+xml;charset-utf-8," + encodeURIComponent(svg.outerHTML);
      return canvas;
    }
    /**
     * Convert an SVG to a canvas. Warning: This happens async!
     *
     * @param {SVGElement} svg
     * @param {HTMLImageElement} canvas
     * @param {Number} width
     * @param {Number} height
     */
    static svgToImg(svg, img, width, height) {
      let canvas = document.createElement("canvas");
      this.svgToCanvas(svg, canvas, width, height, () => {
        img.src = canvas.toDataURL("image/png");
      });
    }
    /**
     * Create an SVG element containing text.
     * @param {String} text
     * @param {*} themeManager
     * @param {*} options
     * @returns {{svg: SVGElement, width: Number, height: Number}} The SVG element containing the text and its dimensions.
     */
    static writeText(text, themeManager, fontSize, fontFamily, maxWidth = Number.MAX_SAFE_INTEGER) {
      let svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      let style = document.createElementNS("http://www.w3.org/2000/svg", "style");
      style.appendChild(document.createTextNode(`
            .text {
                font: ${fontSize}pt ${fontFamily};
                dominant-baseline: ideographic;
            }
        `));
      svg.appendChild(style);
      let textElem = document.createElementNS("http://www.w3.org/2000/svg", "text");
      textElem.setAttributeNS(null, "class", "text");
      let maxLineWidth = 0;
      let totalHeight = 0;
      let lines = [];
      text.split("\n").forEach((line) => {
        let dims = _SvgWrapper.measureText(line, fontSize, fontFamily, 1);
        if (dims.width >= maxWidth) {
          let totalWordsWidth = 0;
          let maxWordsHeight = 0;
          let words = line.split(" ");
          let offset = 0;
          for (let i = 0; i < words.length; i++) {
            let wordDims = _SvgWrapper.measureText(words[i], fontSize, fontFamily, 1);
            if (totalWordsWidth + wordDims.width > maxWidth) {
              lines.push({
                text: words.slice(offset, i).join(" "),
                width: totalWordsWidth,
                height: maxWordsHeight
              });
              totalWordsWidth = 0;
              maxWordsHeight = 0;
              offset = i;
            }
            if (wordDims.height > maxWordsHeight) {
              maxWordsHeight = wordDims.height;
            }
            totalWordsWidth += wordDims.width;
          }
          if (offset < words.length) {
            lines.push({
              text: words.slice(offset, words.length).join(" "),
              width: totalWordsWidth,
              height: maxWordsHeight
            });
          }
        } else {
          lines.push({
            text: line,
            width: dims.width,
            height: dims.height
          });
        }
      });
      lines.forEach((line) => {
        totalHeight += line.height;
        let tspanElem = document.createElementNS("http://www.w3.org/2000/svg", "tspan");
        tspanElem.setAttributeNS(null, "fill", themeManager.getColor("C"));
        tspanElem.textContent = line.text;
        tspanElem.setAttributeNS(null, "x", "0px");
        tspanElem.setAttributeNS(null, "y", `${totalHeight}px`);
        textElem.appendChild(tspanElem);
        if (line.width > maxLineWidth) {
          maxLineWidth = line.width;
        }
      });
      svg.appendChild(textElem);
      return { svg, width: maxLineWidth, height: totalHeight };
    }
  };

  // node_modules/smiles-drawer/src/SvgDrawer.js
  var SvgDrawer = class {
    constructor(options, clear = true) {
      this.preprocessor = new DrawerBase(options);
      this.opts = this.preprocessor.opts;
      this.clear = clear;
      this.svgWrapper = null;
    }
    /**
     * Draws the parsed smiles data to an svg element.
     *
     * @param {Object} data The tree returned by the smiles parser.
     * @param {?(String|SVGElement)} target The id of the HTML svg element the structure is drawn to - or the element itself.
     * @param {String} themeName='dark' The name of the theme to use. Built-in themes are 'light' and 'dark'.
     * @param {Boolean} infoOnly=false Only output info on the molecule without drawing anything to the canvas.
     *
     * @returns {SVGElement} The svg element
     */
    draw(data, target, themeName = "light", weights = null, infoOnly = false, highlight_atoms = [], weightsNormalized = false) {
      if (target === null || target === "svg") {
        target = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        target.setAttribute("xmlns", "http://www.w3.org/2000/svg");
        target.setAttribute("xmlns:xlink", "http://www.w3.org/1999/xlink");
        target.setAttributeNS(null, "width", this.opts.width);
        target.setAttributeNS(null, "height", this.opts.height);
      } else if (target instanceof String) {
        target = document.getElementById(target);
      }
      let optionBackup = {
        padding: this.opts.padding,
        compactDrawing: this.opts.compactDrawing
      };
      if (weights !== null) {
        this.opts.padding += this.opts.weights.additionalPadding;
        this.opts.compactDrawing = false;
      }
      let preprocessor = this.preprocessor;
      preprocessor.initDraw(data, themeName, infoOnly, highlight_atoms);
      if (!infoOnly) {
        this.themeManager = new ThemeManager(this.opts.themes, themeName);
        if (this.svgWrapper === null || this.clear) {
          this.svgWrapper = new SvgWrapper(this.themeManager, target, this.opts, this.clear);
        }
      }
      preprocessor.processGraph();
      this.svgWrapper.determineDimensions(preprocessor.graph.vertices);
      this.drawAtomHighlights(preprocessor.opts.debug);
      this.drawEdges(preprocessor.opts.debug);
      this.drawVertices(preprocessor.opts.debug);
      if (weights !== null) {
        this.drawWeights(weights, weightsNormalized);
      }
      if (preprocessor.opts.debug) {
        console.debug("SvgDrawer::draw()", {
          graph: preprocessor.graph,
          rings: preprocessor.rings,
          ringConnections: preprocessor.ringConnections
        });
      }
      this.svgWrapper.constructSvg();
      if (weights !== null) {
        this.opts.padding = optionBackup.padding;
        this.opts.compactDrawing = optionBackup.padding;
      }
      return target;
    }
    /**
     * Draws the parsed smiles data to a canvas element.
     *
     * @param {Object} data The tree returned by the smiles parser.
     * @param {(String|HTMLCanvasElement)} target The id of the HTML canvas element the structure is drawn to - or the element itself.
     * @param {String} themeName='dark' The name of the theme to use. Built-in themes are 'light' and 'dark'.
     * @param {Boolean} infoOnly=false Only output info on the molecule without drawing anything to the canvas.
     */
    drawCanvas(data, target, themeName = "light", infoOnly = false) {
      let canvas = null;
      if (typeof target === "string" || target instanceof String) {
        canvas = document.getElementById(target);
      } else {
        canvas = target;
      }
      let svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svg.setAttribute("xmlns", "http://www.w3.org/2000/svg");
      svg.setAttributeNS(null, "viewBox", "0 0 500 500");
      svg.setAttributeNS(null, "width", "500");
      svg.setAttributeNS(null, "height", "500");
      svg.setAttributeNS(null, "style", "visibility: hidden: position: absolute; left: -1000px");
      document.body.appendChild(svg);
      this.draw(data, svg, themeName, infoOnly);
      this.svgWrapper.toCanvas(canvas, this.opts.width, this.opts.height);
      document.body.removeChild(svg);
      return target;
    }
    /**
     * Draws a ring inside a provided ring, indicating aromaticity.
     *
     * @param {Ring} ring A ring.
     */
    drawAromaticityRing(ring) {
      let svgWrapper = this.svgWrapper;
      svgWrapper.drawRing(ring.center.x, ring.center.y, ring.getSize());
    }
    /**
     * Draw the actual edges as bonds.
     *
     * @param {Boolean} debug A boolean indicating whether or not to draw debug helpers.
     */
    drawEdges(debug) {
      let preprocessor = this.preprocessor, graph = preprocessor.graph, rings = preprocessor.rings, drawn = Array(this.preprocessor.graph.edges.length);
      drawn.fill(false);
      graph.traverseBF(0, (vertex) => {
        let edges = graph.getEdges(vertex.id);
        for (let i = 0; i < edges.length; i++) {
          let edgeId = edges[i];
          if (!drawn[edgeId]) {
            drawn[edgeId] = true;
            this.drawEdge(edgeId, debug);
          }
        }
      });
      if (!preprocessor.bridgedRing) {
        for (let i = 0; i < rings.length; i++) {
          let ring = rings[i];
          if (preprocessor.isRingAromatic(ring)) {
            this.drawAromaticityRing(ring);
          }
        }
      }
    }
    /**
     * Draw the an edge as a bond.
     *
     * @param {Number} edgeId An edge id.
     * @param {Boolean} debug A boolean indicating whether or not to draw debug helpers.
     */
    drawEdge(edgeId, debug) {
      let preprocessor = this.preprocessor, opts = preprocessor.opts, svgWrapper = this.svgWrapper, edge = preprocessor.graph.edges[edgeId], vertexA = preprocessor.graph.vertices[edge.sourceId], vertexB = preprocessor.graph.vertices[edge.targetId], elementA = vertexA.value.element, elementB = vertexB.value.element;
      if ((!vertexA.value.isDrawn || !vertexB.value.isDrawn) && preprocessor.opts.atomVisualization === "default") {
        return;
      }
      let a = vertexA.position, b = vertexB.position, normals = preprocessor.getEdgeNormals(edge), sides = ArrayHelper.clone(normals);
      sides[0].multiplyScalar(10).add(a);
      sides[1].multiplyScalar(10).add(a);
      if (edge.bondType === "=" || preprocessor.getRingbondType(vertexA, vertexB) === "=" || edge.isPartOfAromaticRing && preprocessor.bridgedRing) {
        let inRing = preprocessor.areVerticesInSameRing(vertexA, vertexB);
        let s = preprocessor.chooseSide(vertexA, vertexB, sides);
        if (inRing) {
          let lcr = preprocessor.getLargestOrAromaticCommonRing(vertexA, vertexB);
          let center = lcr.center;
          normals[0].multiplyScalar(opts.bondSpacing);
          normals[1].multiplyScalar(opts.bondSpacing);
          let line = null;
          if (center.sameSideAs(vertexA.position, vertexB.position, Vector2.add(a, normals[0]))) {
            line = new Line(Vector2.add(a, normals[0]), Vector2.add(b, normals[0]), elementA, elementB);
          } else {
            line = new Line(Vector2.add(a, normals[1]), Vector2.add(b, normals[1]), elementA, elementB);
          }
          line.shorten(opts.bondLength - opts.shortBondLength * opts.bondLength);
          if (edge.isPartOfAromaticRing) {
            svgWrapper.drawLine(line, true);
          } else {
            svgWrapper.drawLine(line);
          }
          svgWrapper.drawLine(new Line(a, b, elementA, elementB));
        } else if (edge.center || vertexA.isTerminal() && vertexB.isTerminal() || s.anCount == 0 && s.bnCount > 1 || s.bnCount == 0 && s.anCount > 1) {
          this.multiplyNormals(normals, opts.halfBondSpacing);
          let lineA = new Line(Vector2.add(a, normals[0]), Vector2.add(b, normals[0]), elementA, elementB), lineB = new Line(Vector2.add(a, normals[1]), Vector2.add(b, normals[1]), elementA, elementB);
          svgWrapper.drawLine(lineA);
          svgWrapper.drawLine(lineB);
        } else if (s.sideCount[0] > s.sideCount[1] || s.totalSideCount[0] > s.totalSideCount[1]) {
          this.multiplyNormals(normals, opts.bondSpacing);
          let line = new Line(Vector2.add(a, normals[0]), Vector2.add(b, normals[0]), elementA, elementB);
          line.shorten(opts.bondLength - opts.shortBondLength * opts.bondLength);
          svgWrapper.drawLine(line);
          svgWrapper.drawLine(new Line(a, b, elementA, elementB));
        } else if (s.sideCount[0] < s.sideCount[1] || s.totalSideCount[0] <= s.totalSideCount[1]) {
          this.multiplyNormals(normals, opts.bondSpacing);
          let line = new Line(Vector2.add(a, normals[1]), Vector2.add(b, normals[1]), elementA, elementB);
          line.shorten(opts.bondLength - opts.shortBondLength * opts.bondLength);
          svgWrapper.drawLine(line);
          svgWrapper.drawLine(new Line(a, b, elementA, elementB));
        }
      } else if (edge.bondType === "#") {
        normals[0].multiplyScalar(opts.bondSpacing / 1.5);
        normals[1].multiplyScalar(opts.bondSpacing / 1.5);
        let lineA = new Line(Vector2.add(a, normals[0]), Vector2.add(b, normals[0]), elementA, elementB);
        let lineB = new Line(Vector2.add(a, normals[1]), Vector2.add(b, normals[1]), elementA, elementB);
        svgWrapper.drawLine(lineA);
        svgWrapper.drawLine(lineB);
        svgWrapper.drawLine(new Line(a, b, elementA, elementB));
      } else if (edge.bondType === ".") {
      } else {
        let isChiralCenterA = vertexA.value.isStereoCenter;
        let isChiralCenterB = vertexB.value.isStereoCenter;
        if (edge.wedge === "up") {
          svgWrapper.drawWedge(new Line(a, b, elementA, elementB, isChiralCenterA, isChiralCenterB));
        } else if (edge.wedge === "down") {
          svgWrapper.drawDashedWedge(new Line(a, b, elementA, elementB, isChiralCenterA, isChiralCenterB));
        } else {
          svgWrapper.drawLine(new Line(a, b, elementA, elementB, isChiralCenterA, isChiralCenterB));
        }
      }
      if (debug) {
        let midpoint = Vector2.midpoint(a, b);
        svgWrapper.drawDebugText(midpoint.x, midpoint.y, "e: " + edgeId);
      }
    }
    /**
     * Draw the highlights for atoms to the canvas.
     *
     * @param {Boolean} debug
     */
    drawAtomHighlights(debug) {
      let preprocessor = this.preprocessor;
      let graph = preprocessor.graph;
      let svgWrapper = this.svgWrapper;
      for (let i = 0; i < graph.vertices.length; i++) {
        let vertex = graph.vertices[i];
        let atom = vertex.value;
        for (let j = 0; j < preprocessor.highlight_atoms.length; j++) {
          let highlight = preprocessor.highlight_atoms[j];
          if (atom.class === highlight[0]) {
            svgWrapper.drawAtomHighlight(vertex.position.x, vertex.position.y, highlight[1]);
          }
        }
      }
    }
    /**
     * Draws the vertices representing atoms to the canvas.
     *
     * @param {Boolean} debug A boolean indicating whether or not to draw debug messages to the canvas.
     */
    drawVertices(debug) {
      let preprocessor = this.preprocessor, opts = preprocessor.opts, graph = preprocessor.graph, rings = preprocessor.rings, svgWrapper = this.svgWrapper;
      for (let i = 0; i < graph.vertices.length; i++) {
        let vertex = graph.vertices[i];
        let atom = vertex.value;
        let charge = 0;
        let isotope = 0;
        let bondCount = vertex.value.bondCount;
        let element = atom.element;
        let hydrogens = Atom.maxBonds[element] - bondCount;
        let dir = vertex.getTextDirection(graph.vertices, atom.hasAttachedPseudoElements);
        let isTerminal = opts.terminalCarbons || element !== "C" || atom.hasAttachedPseudoElements ? vertex.isTerminal() : false;
        let isCarbon = atom.element === "C";
        if (atom.element === "N" && atom.isPartOfAromaticRing) {
          hydrogens = 0;
        }
        if (atom.bracket) {
          hydrogens = atom.bracket.hcount;
          charge = atom.bracket.charge;
          isotope = atom.bracket.isotope;
        }
        if (charge || isotope || graph.vertices.length < 3) {
          isCarbon = false;
        }
        if (opts.atomVisualization === "allballs") {
          svgWrapper.drawBall(vertex.position.x, vertex.position.y, element);
        } else if (atom.isDrawn && (!isCarbon || atom.drawExplicit || isTerminal || atom.hasAttachedPseudoElements) || graph.vertices.length === 1) {
          if (opts.atomVisualization === "default") {
            let attachedPseudoElements = atom.getAttachedPseudoElements();
            if (atom.hasAttachedPseudoElements && graph.vertices.length === Object.keys(attachedPseudoElements).length + 1) {
              dir = "right";
            }
            svgWrapper.drawText(
              vertex.position.x,
              vertex.position.y,
              element,
              hydrogens,
              dir,
              isTerminal,
              charge,
              isotope,
              graph.vertices.length,
              attachedPseudoElements
            );
          } else if (opts.atomVisualization === "balls") {
            svgWrapper.drawBall(vertex.position.x, vertex.position.y, element);
          }
        } else if (vertex.getNeighbourCount() === 2 && vertex.forcePositioned == true) {
          let a = graph.vertices[vertex.neighbours[0]].position;
          let b = graph.vertices[vertex.neighbours[1]].position;
          let angle = Vector2.threePointangle(vertex.position, a, b);
          if (Math.abs(Math.PI - angle) < 0.1) {
            svgWrapper.drawPoint(vertex.position.x, vertex.position.y, element);
          }
        }
        if (debug) {
          let value = "v: " + vertex.id + " " + ArrayHelper.print(atom.ringbonds);
          svgWrapper.drawDebugText(vertex.position.x, vertex.position.y, value);
        }
      }
      if (opts.debug) {
        for (let i = 0; i < rings.length; i++) {
          let center = rings[i].center;
          svgWrapper.drawDebugPoint(center.x, center.y, "r: " + rings[i].id);
        }
      }
    }
    /**
     * Draw the weights on a background image.
     * @param {Number[]} weights The weights assigned to each atom.
     */
    drawWeights(weights, weightsNormalized) {
      if (!weights) {
        return;
      }
      if (weights.every((w) => w === 0)) {
        return;
      }
      if (weights.length !== this.preprocessor.graph.atomIdxToVertexId.length) {
        throw new Error("The number of weights supplied must be equal to the number of (heavy) atoms in the molecule.");
      }
      let points = [];
      for (const atomIdx of this.preprocessor.graph.atomIdxToVertexId) {
        let vertex = this.preprocessor.graph.vertices[atomIdx];
        points.push(
          new Vector2(
            vertex.position.x - this.svgWrapper.minX,
            vertex.position.y - this.svgWrapper.minY
          )
        );
      }
      let gd = new GaussDrawer(
        points,
        weights,
        this.svgWrapper.drawingWidth,
        this.svgWrapper.drawingHeight,
        this.opts.weights.sigma,
        this.opts.weights.interval,
        this.opts.weights.colormap,
        this.opts.weights.opacity,
        weightsNormalized
      );
      gd.draw();
      this.svgWrapper.addLayer(gd.getSVG());
    }
    /**
     * Returns the total overlap score of the current molecule.
     *
     * @returns {Number} The overlap score.
     */
    getTotalOverlapScore() {
      return this.preprocessor.getTotalOverlapScore();
    }
    /**
     * Returns the molecular formula of the loaded molecule as a string.
     *
     * @returns {String} The molecular formula.
     */
    getMolecularFormula(graph = null) {
      return this.preprocessor.getMolecularFormula(graph);
    }
    /**
     * @param {Array} normals list of normals to multiply
     * @param {Number} spacing value to multiply normals by
     */
    multiplyNormals(normals, spacing) {
      normals[0].multiplyScalar(spacing);
      normals[1].multiplyScalar(spacing);
    }
  };

  // node_modules/smiles-drawer/src/Drawer.js
  var Drawer = class {
    /**
     * The constructor for the class SmilesDrawer.
     *
     * @param {Object} options An object containing custom values for different options. It is merged with the default options.
     */
    constructor(options) {
      this.svgDrawer = new SvgDrawer(options);
    }
    /**
     * Draws the parsed smiles data to a canvas element.
     *
     * @param {Object} data The tree returned by the smiles parser.
     * @param {string|String|HTMLCanvasElement} target The id of the HTML canvas element the structure is drawn to - or the element itself.
     * @param {String} themeName='dark' The name of the theme to use. Built-in themes are 'light' and 'dark'.
     * @param {Boolean} infoOnly=false Only output info on the molecule without drawing anything to the canvas.
     */
    draw(data, target, themeName = "light", infoOnly = false, highlight_atoms = []) {
      let element = null;
      let canvas = null;
      if (target instanceof String) {
        element = document.getElementById(target.valueOf());
      } else if (typeof target === "string") {
        element = document.getElementById(target);
      } else {
        element = target;
      }
      if (element instanceof HTMLCanvasElement) {
        canvas = element;
      } else {
        throw Error("First argument was not a canvas or the ID of a canvas.");
      }
      let svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svg.setAttribute("xmlns", "http://www.w3.org/2000/svg");
      svg.setAttributeNS(null, "viewBox", "0 0 " + this.svgDrawer.opts.width + " " + this.svgDrawer.opts.height);
      svg.setAttributeNS(null, "width", this.svgDrawer.opts.width + "");
      svg.setAttributeNS(null, "height", this.svgDrawer.opts.height + "");
      this.svgDrawer.draw(data, svg, themeName, null, infoOnly, highlight_atoms);
      this.svgDrawer.svgWrapper.toCanvas(canvas, this.svgDrawer.opts.width, this.svgDrawer.opts.height);
    }
    /**
     * Returns the total overlap score of the current molecule.
     *
     * @returns {Number} The overlap score.
     */
    getTotalOverlapScore() {
      return this.svgDrawer.getTotalOverlapScore();
    }
    /**
     * Returns the molecular formula of the loaded molecule as a string.
     *
     * @returns {String} The molecular formula.
     */
    getMolecularFormula() {
      return this.svgDrawer.getMolecularFormula();
    }
  };

  // node_modules/smiles-drawer/src/Parser.js
  var Parser_default = (function() {
    "use strict";
    function peg$subclass(child, parent) {
      function ctor() {
        this.constructor = child;
      }
      ctor.prototype = parent.prototype;
      child.prototype = new ctor();
    }
    function peg$SyntaxError(message, expected, found, location) {
      this.message = message;
      this.expected = expected;
      this.found = found;
      this.location = location;
      this.name = "SyntaxError";
      if (typeof Error.captureStackTrace === "function") {
        Error.captureStackTrace(this, peg$SyntaxError);
      }
    }
    peg$subclass(peg$SyntaxError, Error);
    peg$SyntaxError.buildMessage = function(expected, found) {
      var DESCRIBE_EXPECTATION_FNS = {
        literal: function(expectation) {
          return '"' + literalEscape(expectation.text) + '"';
        },
        "class": function(expectation) {
          var escapedParts = "", i;
          for (i = 0; i < expectation.parts.length; i++) {
            escapedParts += expectation.parts[i] instanceof Array ? classEscape(expectation.parts[i][0]) + "-" + classEscape(expectation.parts[i][1]) : classEscape(expectation.parts[i]);
          }
          return "[" + (expectation.inverted ? "^" : "") + escapedParts + "]";
        },
        any: function(expectation) {
          return "any character";
        },
        end: function(expectation) {
          return "end of input";
        },
        other: function(expectation) {
          return expectation.description;
        }
      };
      function hex(ch) {
        return ch.charCodeAt(0).toString(16).toUpperCase();
      }
      function literalEscape(s) {
        return s.replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\0/g, "\\0").replace(/\t/g, "\\t").replace(/\n/g, "\\n").replace(/\r/g, "\\r").replace(/[\x00-\x0F]/g, function(ch) {
          return "\\x0" + hex(ch);
        }).replace(/[\x10-\x1F\x7F-\x9F]/g, function(ch) {
          return "\\x" + hex(ch);
        });
      }
      function classEscape(s) {
        return s.replace(/\\/g, "\\\\").replace(/\]/g, "\\]").replace(/\^/g, "\\^").replace(/-/g, "\\-").replace(/\0/g, "\\0").replace(/\t/g, "\\t").replace(/\n/g, "\\n").replace(/\r/g, "\\r").replace(/[\x00-\x0F]/g, function(ch) {
          return "\\x0" + hex(ch);
        }).replace(/[\x10-\x1F\x7F-\x9F]/g, function(ch) {
          return "\\x" + hex(ch);
        });
      }
      function describeExpectation(expectation) {
        return DESCRIBE_EXPECTATION_FNS[expectation.type](expectation);
      }
      function describeExpected(expected2) {
        var descriptions = new Array(expected2.length), i, j;
        for (i = 0; i < expected2.length; i++) {
          descriptions[i] = describeExpectation(expected2[i]);
        }
        descriptions.sort();
        if (descriptions.length > 0) {
          for (i = 1, j = 1; i < descriptions.length; i++) {
            if (descriptions[i - 1] !== descriptions[i]) {
              descriptions[j] = descriptions[i];
              j++;
            }
          }
          descriptions.length = j;
        }
        switch (descriptions.length) {
          case 1:
            return descriptions[0];
          case 2:
            return descriptions[0] + " or " + descriptions[1];
          default:
            return descriptions.slice(0, -1).join(", ") + ", or " + descriptions[descriptions.length - 1];
        }
      }
      function describeFound(found2) {
        return found2 ? '"' + literalEscape(found2) + '"' : "end of input";
      }
      return "Expected " + describeExpected(expected) + " but " + describeFound(found) + " found.";
    };
    function peg$parse(input, options) {
      options = options !== void 0 ? options : {};
      var nOpenParentheses = input.split("(").length - 1;
      var nCloseParentheses = input.split(")").length - 1;
      if (nOpenParentheses !== nCloseParentheses) {
        throw peg$buildSimpleError("The number of opening parentheses does not match the number of closing parentheses.", 0);
      }
      var peg$FAILED = {}, peg$startRuleFunctions = {
        chain: peg$parsechain
      }, peg$startRuleFunction = peg$parsechain, peg$c0 = function(s) {
        var branches = [];
        var rings = [];
        for (var i = 0; i < s[1].length; i++) {
          branches.push(s[1][i]);
        }
        for (var i = 0; i < s[2].length; i++) {
          var bond = s[2][i][0] ? s[2][i][0] : "-";
          rings.push({
            "bond": bond,
            "id": s[2][i][1]
          });
        }
        for (var i = 0; i < s[3].length; i++) {
          branches.push(s[3][i]);
        }
        for (var i = 0; i < s[6].length; i++) {
          branches.push(s[6][i]);
        }
        return {
          "atom": s[0],
          "isBracket": s[0].element ? true : false,
          "branches": branches,
          "branchCount": branches.length,
          "ringbonds": rings,
          "ringbondCount": rings.length,
          "bond": s[4] ? s[4] : "-",
          "next": s[5],
          "hasNext": s[5] ? true : false
        };
      }, peg$c1 = "(", peg$c2 = peg$literalExpectation("(", false), peg$c3 = ")", peg$c4 = peg$literalExpectation(")", false), peg$c5 = function(b) {
        var bond = b[1] ? b[1] : "-";
        b[2].branchBond = bond;
        return b[2];
      }, peg$c6 = function(a) {
        return a;
      }, peg$c7 = /^[\-=#$:\/\\.]/, peg$c8 = peg$classExpectation(["-", "=", "#", "$", ":", "/", "\\", "."], false, false), peg$c9 = function(b) {
        return b;
      }, peg$c10 = "[", peg$c11 = peg$literalExpectation("[", false), peg$c12 = "se", peg$c13 = peg$literalExpectation("se", false), peg$c14 = "as", peg$c15 = peg$literalExpectation("as", false), peg$c16 = "]", peg$c17 = peg$literalExpectation("]", false), peg$c18 = function(b) {
        return {
          "isotope": b[1],
          "element": b[2],
          "chirality": b[3],
          "hcount": b[4],
          "charge": b[5],
          "class": b[6]
        };
      }, peg$c19 = "B", peg$c20 = peg$literalExpectation("B", false), peg$c21 = "r", peg$c22 = peg$literalExpectation("r", false), peg$c23 = "C", peg$c24 = peg$literalExpectation("C", false), peg$c25 = "l", peg$c26 = peg$literalExpectation("l", false), peg$c27 = /^[NOPSFI]/, peg$c28 = peg$classExpectation(["N", "O", "P", "S", "F", "I"], false, false), peg$c29 = function(o) {
        if (o.length > 1) return o.join("");
        return o;
      }, peg$c30 = /^[bcnops]/, peg$c31 = peg$classExpectation(["b", "c", "n", "o", "p", "s"], false, false), peg$c32 = "*", peg$c33 = peg$literalExpectation("*", false), peg$c34 = function(w) {
        return w;
      }, peg$c35 = /^[A-Z]/, peg$c36 = peg$classExpectation([
        ["A", "Z"]
      ], false, false), peg$c37 = /^[a-z]/, peg$c38 = peg$classExpectation([
        ["a", "z"]
      ], false, false), peg$c39 = function(e) {
        return e.join("");
      }, peg$c40 = "%", peg$c41 = peg$literalExpectation("%", false), peg$c42 = /^[1-9]/, peg$c43 = peg$classExpectation([
        ["1", "9"]
      ], false, false), peg$c44 = /^[0-9]/, peg$c45 = peg$classExpectation([
        ["0", "9"]
      ], false, false), peg$c46 = function(r) {
        if (r.length == 1) return Number(r);
        return Number(r.join("").replace("%", ""));
      }, peg$c47 = "@", peg$c48 = peg$literalExpectation("@", false), peg$c49 = "TH", peg$c50 = peg$literalExpectation("TH", false), peg$c51 = /^[12]/, peg$c52 = peg$classExpectation(["1", "2"], false, false), peg$c53 = "AL", peg$c54 = peg$literalExpectation("AL", false), peg$c55 = "SP", peg$c56 = peg$literalExpectation("SP", false), peg$c57 = /^[1-3]/, peg$c58 = peg$classExpectation([
        ["1", "3"]
      ], false, false), peg$c59 = "TB", peg$c60 = peg$literalExpectation("TB", false), peg$c61 = "OH", peg$c62 = peg$literalExpectation("OH", false), peg$c63 = function(c) {
        if (!c[1]) return "@";
        if (c[1] == "@") return "@@";
        return c[1].join("").replace(",", "");
      }, peg$c64 = function(c) {
        return c;
      }, peg$c65 = "+", peg$c66 = peg$literalExpectation("+", false), peg$c67 = function(c) {
        if (!c[1]) return 1;
        if (c[1] != "+") return Number(c[1].join(""));
        return 2;
      }, peg$c68 = "-", peg$c69 = peg$literalExpectation("-", false), peg$c70 = function(c) {
        if (!c[1]) return -1;
        if (c[1] != "-") return -Number(c[1].join(""));
        return -2;
      }, peg$c71 = "H", peg$c72 = peg$literalExpectation("H", false), peg$c73 = function(h) {
        if (h[1]) return Number(h[1]);
        return 1;
      }, peg$c74 = ":", peg$c75 = peg$literalExpectation(":", false), peg$c76 = /^[0]/, peg$c77 = peg$classExpectation(["0"], false, false), peg$c78 = function(c) {
        return Number(c[1][0] + c[1][1].join(""));
      }, peg$c79 = function(i) {
        return Number(i.join(""));
      }, peg$currPos = 0, peg$savedPos = 0, peg$posDetailsCache = [{
        line: 1,
        column: 1
      }], peg$maxFailPos = 0, peg$maxFailExpected = [], peg$silentFails = 0, peg$result;
      if ("startRule" in options) {
        if (!(options.startRule in peg$startRuleFunctions)) {
          throw new Error(`Can't start parsing from rule "` + options.startRule + '".');
        }
        peg$startRuleFunction = peg$startRuleFunctions[options.startRule];
      }
      function text() {
        return input.substring(peg$savedPos, peg$currPos);
      }
      function location() {
        return peg$computeLocation(peg$savedPos, peg$currPos);
      }
      function expected(description, location2) {
        location2 = location2 !== void 0 ? location2 : peg$computeLocation(peg$savedPos, peg$currPos);
        throw peg$buildStructuredError(
          [peg$otherExpectation(description)],
          input.substring(peg$savedPos, peg$currPos),
          location2
        );
      }
      function error(message, location2) {
        location2 = location2 !== void 0 ? location2 : peg$computeLocation(peg$savedPos, peg$currPos);
        throw peg$buildSimpleError(message, location2);
      }
      function peg$literalExpectation(text2, ignoreCase) {
        return {
          type: "literal",
          text: text2,
          ignoreCase
        };
      }
      function peg$classExpectation(parts, inverted, ignoreCase) {
        return {
          type: "class",
          parts,
          inverted,
          ignoreCase
        };
      }
      function peg$anyExpectation() {
        return {
          type: "any"
        };
      }
      function peg$endExpectation() {
        return {
          type: "end"
        };
      }
      function peg$otherExpectation(description) {
        return {
          type: "other",
          description
        };
      }
      function peg$computePosDetails(pos) {
        var details = peg$posDetailsCache[pos], p;
        if (details) {
          return details;
        } else {
          p = pos - 1;
          while (!peg$posDetailsCache[p]) {
            p--;
          }
          details = peg$posDetailsCache[p];
          details = {
            line: details.line,
            column: details.column
          };
          while (p < pos) {
            if (input.charCodeAt(p) === 10) {
              details.line++;
              details.column = 1;
            } else {
              details.column++;
            }
            p++;
          }
          peg$posDetailsCache[pos] = details;
          return details;
        }
      }
      function peg$computeLocation(startPos, endPos) {
        var startPosDetails = peg$computePosDetails(startPos), endPosDetails = peg$computePosDetails(endPos);
        return {
          start: {
            offset: startPos,
            line: startPosDetails.line,
            column: startPosDetails.column
          },
          end: {
            offset: endPos,
            line: endPosDetails.line,
            column: endPosDetails.column
          }
        };
      }
      function peg$fail(expected2) {
        if (peg$currPos < peg$maxFailPos) {
          return;
        }
        if (peg$currPos > peg$maxFailPos) {
          peg$maxFailPos = peg$currPos;
          peg$maxFailExpected = [];
        }
        peg$maxFailExpected.push(expected2);
      }
      function peg$buildSimpleError(message, location2) {
        return new peg$SyntaxError(message, null, null, location2);
      }
      function peg$buildStructuredError(expected2, found, location2) {
        return new peg$SyntaxError(
          peg$SyntaxError.buildMessage(expected2, found),
          expected2,
          found,
          location2
        );
      }
      function peg$parsechain() {
        var s0, s1, s2, s3, s4, s5, s6, s7, s8, s9;
        s0 = peg$currPos;
        s1 = peg$currPos;
        s2 = peg$parseatom();
        if (s2 !== peg$FAILED) {
          s3 = [];
          s4 = peg$parsebranch();
          while (s4 !== peg$FAILED) {
            s3.push(s4);
            s4 = peg$parsebranch();
          }
          if (s3 !== peg$FAILED) {
            s4 = [];
            s5 = peg$currPos;
            s6 = peg$parsebond();
            if (s6 === peg$FAILED) {
              s6 = null;
            }
            if (s6 !== peg$FAILED) {
              s7 = peg$parsering();
              if (s7 !== peg$FAILED) {
                s6 = [s6, s7];
                s5 = s6;
              } else {
                peg$currPos = s5;
                s5 = peg$FAILED;
              }
            } else {
              peg$currPos = s5;
              s5 = peg$FAILED;
            }
            while (s5 !== peg$FAILED) {
              s4.push(s5);
              s5 = peg$currPos;
              s6 = peg$parsebond();
              if (s6 === peg$FAILED) {
                s6 = null;
              }
              if (s6 !== peg$FAILED) {
                s7 = peg$parsering();
                if (s7 !== peg$FAILED) {
                  s6 = [s6, s7];
                  s5 = s6;
                } else {
                  peg$currPos = s5;
                  s5 = peg$FAILED;
                }
              } else {
                peg$currPos = s5;
                s5 = peg$FAILED;
              }
            }
            if (s4 !== peg$FAILED) {
              s5 = [];
              s6 = peg$parsebranch();
              while (s6 !== peg$FAILED) {
                s5.push(s6);
                s6 = peg$parsebranch();
              }
              if (s5 !== peg$FAILED) {
                s6 = peg$parsebond();
                if (s6 === peg$FAILED) {
                  s6 = null;
                }
                if (s6 !== peg$FAILED) {
                  s7 = peg$parsechain();
                  if (s7 === peg$FAILED) {
                    s7 = null;
                  }
                  if (s7 !== peg$FAILED) {
                    s8 = [];
                    s9 = peg$parsebranch();
                    while (s9 !== peg$FAILED) {
                      s8.push(s9);
                      s9 = peg$parsebranch();
                    }
                    if (s8 !== peg$FAILED) {
                      s2 = [s2, s3, s4, s5, s6, s7, s8];
                      s1 = s2;
                    } else {
                      peg$currPos = s1;
                      s1 = peg$FAILED;
                    }
                  } else {
                    peg$currPos = s1;
                    s1 = peg$FAILED;
                  }
                } else {
                  peg$currPos = s1;
                  s1 = peg$FAILED;
                }
              } else {
                peg$currPos = s1;
                s1 = peg$FAILED;
              }
            } else {
              peg$currPos = s1;
              s1 = peg$FAILED;
            }
          } else {
            peg$currPos = s1;
            s1 = peg$FAILED;
          }
        } else {
          peg$currPos = s1;
          s1 = peg$FAILED;
        }
        if (s1 !== peg$FAILED) {
          peg$savedPos = s0;
          s1 = peg$c0(s1);
        }
        s0 = s1;
        return s0;
      }
      function peg$parsebranch() {
        var s0, s1, s2, s3, s4, s5;
        s0 = peg$currPos;
        s1 = peg$currPos;
        if (input.charCodeAt(peg$currPos) === 40) {
          s2 = peg$c1;
          peg$currPos++;
        } else {
          s2 = peg$FAILED;
          if (peg$silentFails === 0) {
            peg$fail(peg$c2);
          }
        }
        if (s2 !== peg$FAILED) {
          s3 = peg$parsebond();
          if (s3 === peg$FAILED) {
            s3 = null;
          }
          if (s3 !== peg$FAILED) {
            s4 = peg$parsechain();
            if (s4 !== peg$FAILED) {
              if (input.charCodeAt(peg$currPos) === 41) {
                s5 = peg$c3;
                peg$currPos++;
              } else {
                s5 = peg$FAILED;
                if (peg$silentFails === 0) {
                  peg$fail(peg$c4);
                }
              }
              if (s5 !== peg$FAILED) {
                s2 = [s2, s3, s4, s5];
                s1 = s2;
              } else {
                peg$currPos = s1;
                s1 = peg$FAILED;
              }
            } else {
              peg$currPos = s1;
              s1 = peg$FAILED;
            }
          } else {
            peg$currPos = s1;
            s1 = peg$FAILED;
          }
        } else {
          peg$currPos = s1;
          s1 = peg$FAILED;
        }
        if (s1 !== peg$FAILED) {
          peg$savedPos = s0;
          s1 = peg$c5(s1);
        }
        s0 = s1;
        return s0;
      }
      function peg$parseatom() {
        var s0, s1;
        s0 = peg$currPos;
        s1 = peg$parseorganicsymbol();
        if (s1 === peg$FAILED) {
          s1 = peg$parsearomaticsymbol();
          if (s1 === peg$FAILED) {
            s1 = peg$parsebracketatom();
            if (s1 === peg$FAILED) {
              s1 = peg$parsewildcard();
            }
          }
        }
        if (s1 !== peg$FAILED) {
          peg$savedPos = s0;
          s1 = peg$c6(s1);
        }
        s0 = s1;
        return s0;
      }
      function peg$parsebond() {
        var s0, s1;
        s0 = peg$currPos;
        if (peg$c7.test(input.charAt(peg$currPos))) {
          s1 = input.charAt(peg$currPos);
          if (s1 === input.charAt(peg$currPos + 1)) {
            s1 = peg$FAILED;
            if (peg$silentFails === 0) {
              throw peg$buildSimpleError("The parser encountered a bond repetition.", peg$currPos + 1);
            }
          }
          peg$currPos++;
        } else {
          s1 = peg$FAILED;
          if (peg$silentFails === 0) {
            peg$fail(peg$c8);
          }
        }
        if (s1 !== peg$FAILED) {
          peg$savedPos = s0;
          s1 = peg$c9(s1);
        }
        s0 = s1;
        return s0;
      }
      function peg$parsebracketatom() {
        var s0, s1, s2, s3, s4, s5, s6, s7, s8, s9;
        s0 = peg$currPos;
        s1 = peg$currPos;
        if (input.charCodeAt(peg$currPos) === 91) {
          s2 = peg$c10;
          peg$currPos++;
        } else {
          s2 = peg$FAILED;
          if (peg$silentFails === 0) {
            peg$fail(peg$c11);
          }
        }
        if (s2 !== peg$FAILED) {
          s3 = peg$parseisotope();
          if (s3 === peg$FAILED) {
            s3 = null;
          }
          if (s3 !== peg$FAILED) {
            if (input.substr(peg$currPos, 2) === peg$c12) {
              s4 = peg$c12;
              peg$currPos += 2;
            } else {
              s4 = peg$FAILED;
              if (peg$silentFails === 0) {
                peg$fail(peg$c13);
              }
            }
            if (s4 === peg$FAILED) {
              if (input.substr(peg$currPos, 2) === peg$c14) {
                s4 = peg$c14;
                peg$currPos += 2;
              } else {
                s4 = peg$FAILED;
                if (peg$silentFails === 0) {
                  peg$fail(peg$c15);
                }
              }
              if (s4 === peg$FAILED) {
                s4 = peg$parsearomaticsymbol();
                if (s4 === peg$FAILED) {
                  s4 = peg$parseelementsymbol();
                  if (s4 === peg$FAILED) {
                    s4 = peg$parsewildcard();
                  }
                }
              }
            }
            if (s4 !== peg$FAILED) {
              s5 = peg$parsechiral();
              if (s5 === peg$FAILED) {
                s5 = null;
              }
              if (s5 !== peg$FAILED) {
                s6 = peg$parsehcount();
                if (s6 === peg$FAILED) {
                  s6 = null;
                }
                if (s6 !== peg$FAILED) {
                  s7 = peg$parsecharge();
                  if (s7 === peg$FAILED) {
                    s7 = null;
                  }
                  if (s7 !== peg$FAILED) {
                    s8 = peg$parseclass();
                    if (s8 === peg$FAILED) {
                      s8 = null;
                    }
                    if (s8 !== peg$FAILED) {
                      if (input.charCodeAt(peg$currPos) === 93) {
                        s9 = peg$c16;
                        peg$currPos++;
                      } else {
                        s9 = peg$FAILED;
                        if (peg$silentFails === 0) {
                          peg$fail(peg$c17);
                        }
                      }
                      if (s9 !== peg$FAILED) {
                        s2 = [s2, s3, s4, s5, s6, s7, s8, s9];
                        s1 = s2;
                      } else {
                        peg$currPos = s1;
                        s1 = peg$FAILED;
                      }
                    } else {
                      peg$currPos = s1;
                      s1 = peg$FAILED;
                    }
                  } else {
                    peg$currPos = s1;
                    s1 = peg$FAILED;
                  }
                } else {
                  peg$currPos = s1;
                  s1 = peg$FAILED;
                }
              } else {
                peg$currPos = s1;
                s1 = peg$FAILED;
              }
            } else {
              peg$currPos = s1;
              s1 = peg$FAILED;
            }
          } else {
            peg$currPos = s1;
            s1 = peg$FAILED;
          }
        } else {
          peg$currPos = s1;
          s1 = peg$FAILED;
        }
        if (s1 !== peg$FAILED) {
          peg$savedPos = s0;
          s1 = peg$c18(s1);
        }
        s0 = s1;
        return s0;
      }
      function peg$parseorganicsymbol() {
        var s0, s1, s2, s3;
        s0 = peg$currPos;
        s1 = peg$currPos;
        if (input.charCodeAt(peg$currPos) === 66) {
          s2 = peg$c19;
          peg$currPos++;
        } else {
          s2 = peg$FAILED;
          if (peg$silentFails === 0) {
            peg$fail(peg$c20);
          }
        }
        if (s2 !== peg$FAILED) {
          if (input.charCodeAt(peg$currPos) === 114) {
            s3 = peg$c21;
            peg$currPos++;
          } else {
            s3 = peg$FAILED;
            if (peg$silentFails === 0) {
              peg$fail(peg$c22);
            }
          }
          if (s3 === peg$FAILED) {
            s3 = null;
          }
          if (s3 !== peg$FAILED) {
            s2 = [s2, s3];
            s1 = s2;
          } else {
            peg$currPos = s1;
            s1 = peg$FAILED;
          }
        } else {
          peg$currPos = s1;
          s1 = peg$FAILED;
        }
        if (s1 === peg$FAILED) {
          s1 = peg$currPos;
          if (input.charCodeAt(peg$currPos) === 67) {
            s2 = peg$c23;
            peg$currPos++;
          } else {
            s2 = peg$FAILED;
            if (peg$silentFails === 0) {
              peg$fail(peg$c24);
            }
          }
          if (s2 !== peg$FAILED) {
            if (input.charCodeAt(peg$currPos) === 108) {
              s3 = peg$c25;
              peg$currPos++;
            } else {
              s3 = peg$FAILED;
              if (peg$silentFails === 0) {
                peg$fail(peg$c26);
              }
            }
            if (s3 === peg$FAILED) {
              s3 = null;
            }
            if (s3 !== peg$FAILED) {
              s2 = [s2, s3];
              s1 = s2;
            } else {
              peg$currPos = s1;
              s1 = peg$FAILED;
            }
          } else {
            peg$currPos = s1;
            s1 = peg$FAILED;
          }
          if (s1 === peg$FAILED) {
            if (peg$c27.test(input.charAt(peg$currPos))) {
              s1 = input.charAt(peg$currPos);
              peg$currPos++;
            } else {
              s1 = peg$FAILED;
              if (peg$silentFails === 0) {
                peg$fail(peg$c28);
              }
            }
          }
        }
        if (s1 !== peg$FAILED) {
          peg$savedPos = s0;
          s1 = peg$c29(s1);
        }
        s0 = s1;
        return s0;
      }
      function peg$parsearomaticsymbol() {
        var s0, s1;
        s0 = peg$currPos;
        if (peg$c30.test(input.charAt(peg$currPos))) {
          s1 = input.charAt(peg$currPos);
          peg$currPos++;
        } else {
          s1 = peg$FAILED;
          if (peg$silentFails === 0) {
            peg$fail(peg$c31);
          }
        }
        if (s1 !== peg$FAILED) {
          peg$savedPos = s0;
          s1 = peg$c6(s1);
        }
        s0 = s1;
        return s0;
      }
      function peg$parsewildcard() {
        var s0, s1;
        s0 = peg$currPos;
        if (input.charCodeAt(peg$currPos) === 42) {
          s1 = peg$c32;
          peg$currPos++;
        } else {
          s1 = peg$FAILED;
          if (peg$silentFails === 0) {
            peg$fail(peg$c33);
          }
        }
        if (s1 !== peg$FAILED) {
          peg$savedPos = s0;
          s1 = peg$c34(s1);
        }
        s0 = s1;
        return s0;
      }
      function peg$parseelementsymbol() {
        var s0, s1, s2, s3;
        s0 = peg$currPos;
        s1 = peg$currPos;
        if (peg$c35.test(input.charAt(peg$currPos))) {
          s2 = input.charAt(peg$currPos);
          peg$currPos++;
        } else {
          s2 = peg$FAILED;
          if (peg$silentFails === 0) {
            peg$fail(peg$c36);
          }
        }
        if (s2 !== peg$FAILED) {
          if (peg$c37.test(input.charAt(peg$currPos))) {
            s3 = input.charAt(peg$currPos);
            peg$currPos++;
          } else {
            s3 = peg$FAILED;
            if (peg$silentFails === 0) {
              peg$fail(peg$c38);
            }
          }
          if (s3 === peg$FAILED) {
            s3 = null;
          }
          if (s3 !== peg$FAILED) {
            s2 = [s2, s3];
            s1 = s2;
          } else {
            peg$currPos = s1;
            s1 = peg$FAILED;
          }
        } else {
          peg$currPos = s1;
          s1 = peg$FAILED;
        }
        if (s1 !== peg$FAILED) {
          peg$savedPos = s0;
          s1 = peg$c39(s1);
        }
        s0 = s1;
        return s0;
      }
      function peg$parsering() {
        var s0, s1, s2, s3, s4;
        s0 = peg$currPos;
        s1 = peg$currPos;
        if (input.charCodeAt(peg$currPos) === 37) {
          s2 = peg$c40;
          peg$currPos++;
        } else {
          s2 = peg$FAILED;
          if (peg$silentFails === 0) {
            peg$fail(peg$c41);
          }
        }
        if (s2 !== peg$FAILED) {
          if (peg$c42.test(input.charAt(peg$currPos))) {
            s3 = input.charAt(peg$currPos);
            peg$currPos++;
          } else {
            s3 = peg$FAILED;
            if (peg$silentFails === 0) {
              peg$fail(peg$c43);
            }
          }
          if (s3 !== peg$FAILED) {
            if (peg$c44.test(input.charAt(peg$currPos))) {
              s4 = input.charAt(peg$currPos);
              peg$currPos++;
            } else {
              s4 = peg$FAILED;
              if (peg$silentFails === 0) {
                peg$fail(peg$c45);
              }
            }
            if (s4 !== peg$FAILED) {
              s2 = [s2, s3, s4];
              s1 = s2;
            } else {
              peg$currPos = s1;
              s1 = peg$FAILED;
            }
          } else {
            peg$currPos = s1;
            s1 = peg$FAILED;
          }
        } else {
          peg$currPos = s1;
          s1 = peg$FAILED;
        }
        if (s1 === peg$FAILED) {
          if (peg$c44.test(input.charAt(peg$currPos))) {
            s1 = input.charAt(peg$currPos);
            peg$currPos++;
          } else {
            s1 = peg$FAILED;
            if (peg$silentFails === 0) {
              peg$fail(peg$c45);
            }
          }
        }
        if (s1 !== peg$FAILED) {
          peg$savedPos = s0;
          s1 = peg$c46(s1);
        }
        s0 = s1;
        return s0;
      }
      function peg$parsechiral() {
        var s0, s1, s2, s3, s4, s5, s6;
        s0 = peg$currPos;
        s1 = peg$currPos;
        if (input.charCodeAt(peg$currPos) === 64) {
          s2 = peg$c47;
          peg$currPos++;
        } else {
          s2 = peg$FAILED;
          if (peg$silentFails === 0) {
            peg$fail(peg$c48);
          }
        }
        if (s2 !== peg$FAILED) {
          if (input.charCodeAt(peg$currPos) === 64) {
            s3 = peg$c47;
            peg$currPos++;
          } else {
            s3 = peg$FAILED;
            if (peg$silentFails === 0) {
              peg$fail(peg$c48);
            }
          }
          if (s3 === peg$FAILED) {
            s3 = peg$currPos;
            if (input.substr(peg$currPos, 2) === peg$c49) {
              s4 = peg$c49;
              peg$currPos += 2;
            } else {
              s4 = peg$FAILED;
              if (peg$silentFails === 0) {
                peg$fail(peg$c50);
              }
            }
            if (s4 !== peg$FAILED) {
              if (peg$c51.test(input.charAt(peg$currPos))) {
                s5 = input.charAt(peg$currPos);
                peg$currPos++;
              } else {
                s5 = peg$FAILED;
                if (peg$silentFails === 0) {
                  peg$fail(peg$c52);
                }
              }
              if (s5 !== peg$FAILED) {
                s4 = [s4, s5];
                s3 = s4;
              } else {
                peg$currPos = s3;
                s3 = peg$FAILED;
              }
            } else {
              peg$currPos = s3;
              s3 = peg$FAILED;
            }
            if (s3 === peg$FAILED) {
              s3 = peg$currPos;
              if (input.substr(peg$currPos, 2) === peg$c53) {
                s4 = peg$c53;
                peg$currPos += 2;
              } else {
                s4 = peg$FAILED;
                if (peg$silentFails === 0) {
                  peg$fail(peg$c54);
                }
              }
              if (s4 !== peg$FAILED) {
                if (peg$c51.test(input.charAt(peg$currPos))) {
                  s5 = input.charAt(peg$currPos);
                  peg$currPos++;
                } else {
                  s5 = peg$FAILED;
                  if (peg$silentFails === 0) {
                    peg$fail(peg$c52);
                  }
                }
                if (s5 !== peg$FAILED) {
                  s4 = [s4, s5];
                  s3 = s4;
                } else {
                  peg$currPos = s3;
                  s3 = peg$FAILED;
                }
              } else {
                peg$currPos = s3;
                s3 = peg$FAILED;
              }
              if (s3 === peg$FAILED) {
                s3 = peg$currPos;
                if (input.substr(peg$currPos, 2) === peg$c55) {
                  s4 = peg$c55;
                  peg$currPos += 2;
                } else {
                  s4 = peg$FAILED;
                  if (peg$silentFails === 0) {
                    peg$fail(peg$c56);
                  }
                }
                if (s4 !== peg$FAILED) {
                  if (peg$c57.test(input.charAt(peg$currPos))) {
                    s5 = input.charAt(peg$currPos);
                    peg$currPos++;
                  } else {
                    s5 = peg$FAILED;
                    if (peg$silentFails === 0) {
                      peg$fail(peg$c58);
                    }
                  }
                  if (s5 !== peg$FAILED) {
                    s4 = [s4, s5];
                    s3 = s4;
                  } else {
                    peg$currPos = s3;
                    s3 = peg$FAILED;
                  }
                } else {
                  peg$currPos = s3;
                  s3 = peg$FAILED;
                }
                if (s3 === peg$FAILED) {
                  s3 = peg$currPos;
                  if (input.substr(peg$currPos, 2) === peg$c59) {
                    s4 = peg$c59;
                    peg$currPos += 2;
                  } else {
                    s4 = peg$FAILED;
                    if (peg$silentFails === 0) {
                      peg$fail(peg$c60);
                    }
                  }
                  if (s4 !== peg$FAILED) {
                    if (peg$c42.test(input.charAt(peg$currPos))) {
                      s5 = input.charAt(peg$currPos);
                      peg$currPos++;
                    } else {
                      s5 = peg$FAILED;
                      if (peg$silentFails === 0) {
                        peg$fail(peg$c43);
                      }
                    }
                    if (s5 !== peg$FAILED) {
                      if (peg$c44.test(input.charAt(peg$currPos))) {
                        s6 = input.charAt(peg$currPos);
                        peg$currPos++;
                      } else {
                        s6 = peg$FAILED;
                        if (peg$silentFails === 0) {
                          peg$fail(peg$c45);
                        }
                      }
                      if (s6 === peg$FAILED) {
                        s6 = null;
                      }
                      if (s6 !== peg$FAILED) {
                        s4 = [s4, s5, s6];
                        s3 = s4;
                      } else {
                        peg$currPos = s3;
                        s3 = peg$FAILED;
                      }
                    } else {
                      peg$currPos = s3;
                      s3 = peg$FAILED;
                    }
                  } else {
                    peg$currPos = s3;
                    s3 = peg$FAILED;
                  }
                  if (s3 === peg$FAILED) {
                    s3 = peg$currPos;
                    if (input.substr(peg$currPos, 2) === peg$c61) {
                      s4 = peg$c61;
                      peg$currPos += 2;
                    } else {
                      s4 = peg$FAILED;
                      if (peg$silentFails === 0) {
                        peg$fail(peg$c62);
                      }
                    }
                    if (s4 !== peg$FAILED) {
                      if (peg$c42.test(input.charAt(peg$currPos))) {
                        s5 = input.charAt(peg$currPos);
                        peg$currPos++;
                      } else {
                        s5 = peg$FAILED;
                        if (peg$silentFails === 0) {
                          peg$fail(peg$c43);
                        }
                      }
                      if (s5 !== peg$FAILED) {
                        if (peg$c44.test(input.charAt(peg$currPos))) {
                          s6 = input.charAt(peg$currPos);
                          peg$currPos++;
                        } else {
                          s6 = peg$FAILED;
                          if (peg$silentFails === 0) {
                            peg$fail(peg$c45);
                          }
                        }
                        if (s6 === peg$FAILED) {
                          s6 = null;
                        }
                        if (s6 !== peg$FAILED) {
                          s4 = [s4, s5, s6];
                          s3 = s4;
                        } else {
                          peg$currPos = s3;
                          s3 = peg$FAILED;
                        }
                      } else {
                        peg$currPos = s3;
                        s3 = peg$FAILED;
                      }
                    } else {
                      peg$currPos = s3;
                      s3 = peg$FAILED;
                    }
                  }
                }
              }
            }
          }
          if (s3 === peg$FAILED) {
            s3 = null;
          }
          if (s3 !== peg$FAILED) {
            s2 = [s2, s3];
            s1 = s2;
          } else {
            peg$currPos = s1;
            s1 = peg$FAILED;
          }
        } else {
          peg$currPos = s1;
          s1 = peg$FAILED;
        }
        if (s1 !== peg$FAILED) {
          peg$savedPos = s0;
          s1 = peg$c63(s1);
        }
        s0 = s1;
        return s0;
      }
      function peg$parsecharge() {
        var s0, s1;
        s0 = peg$currPos;
        s1 = peg$parseposcharge();
        if (s1 === peg$FAILED) {
          s1 = peg$parsenegcharge();
        }
        if (s1 !== peg$FAILED) {
          peg$savedPos = s0;
          s1 = peg$c64(s1);
        }
        s0 = s1;
        return s0;
      }
      function peg$parseposcharge() {
        var s0, s1, s2, s3, s4, s5;
        s0 = peg$currPos;
        s1 = peg$currPos;
        if (input.charCodeAt(peg$currPos) === 43) {
          s2 = peg$c65;
          peg$currPos++;
        } else {
          s2 = peg$FAILED;
          if (peg$silentFails === 0) {
            peg$fail(peg$c66);
          }
        }
        if (s2 !== peg$FAILED) {
          if (input.charCodeAt(peg$currPos) === 43) {
            s3 = peg$c65;
            peg$currPos++;
          } else {
            s3 = peg$FAILED;
            if (peg$silentFails === 0) {
              peg$fail(peg$c66);
            }
          }
          if (s3 === peg$FAILED) {
            s3 = peg$currPos;
            if (peg$c42.test(input.charAt(peg$currPos))) {
              s4 = input.charAt(peg$currPos);
              peg$currPos++;
            } else {
              s4 = peg$FAILED;
              if (peg$silentFails === 0) {
                peg$fail(peg$c43);
              }
            }
            if (s4 !== peg$FAILED) {
              if (peg$c44.test(input.charAt(peg$currPos))) {
                s5 = input.charAt(peg$currPos);
                peg$currPos++;
              } else {
                s5 = peg$FAILED;
                if (peg$silentFails === 0) {
                  peg$fail(peg$c45);
                }
              }
              if (s5 === peg$FAILED) {
                s5 = null;
              }
              if (s5 !== peg$FAILED) {
                s4 = [s4, s5];
                s3 = s4;
              } else {
                peg$currPos = s3;
                s3 = peg$FAILED;
              }
            } else {
              peg$currPos = s3;
              s3 = peg$FAILED;
            }
          }
          if (s3 === peg$FAILED) {
            s3 = null;
          }
          if (s3 !== peg$FAILED) {
            s2 = [s2, s3];
            s1 = s2;
          } else {
            peg$currPos = s1;
            s1 = peg$FAILED;
          }
        } else {
          peg$currPos = s1;
          s1 = peg$FAILED;
        }
        if (s1 !== peg$FAILED) {
          peg$savedPos = s0;
          s1 = peg$c67(s1);
        }
        s0 = s1;
        return s0;
      }
      function peg$parsenegcharge() {
        var s0, s1, s2, s3, s4, s5;
        s0 = peg$currPos;
        s1 = peg$currPos;
        if (input.charCodeAt(peg$currPos) === 45) {
          s2 = peg$c68;
          peg$currPos++;
        } else {
          s2 = peg$FAILED;
          if (peg$silentFails === 0) {
            peg$fail(peg$c69);
          }
        }
        if (s2 !== peg$FAILED) {
          if (input.charCodeAt(peg$currPos) === 45) {
            s3 = peg$c68;
            peg$currPos++;
          } else {
            s3 = peg$FAILED;
            if (peg$silentFails === 0) {
              peg$fail(peg$c69);
            }
          }
          if (s3 === peg$FAILED) {
            s3 = peg$currPos;
            if (peg$c42.test(input.charAt(peg$currPos))) {
              s4 = input.charAt(peg$currPos);
              peg$currPos++;
            } else {
              s4 = peg$FAILED;
              if (peg$silentFails === 0) {
                peg$fail(peg$c43);
              }
            }
            if (s4 !== peg$FAILED) {
              if (peg$c44.test(input.charAt(peg$currPos))) {
                s5 = input.charAt(peg$currPos);
                peg$currPos++;
              } else {
                s5 = peg$FAILED;
                if (peg$silentFails === 0) {
                  peg$fail(peg$c45);
                }
              }
              if (s5 === peg$FAILED) {
                s5 = null;
              }
              if (s5 !== peg$FAILED) {
                s4 = [s4, s5];
                s3 = s4;
              } else {
                peg$currPos = s3;
                s3 = peg$FAILED;
              }
            } else {
              peg$currPos = s3;
              s3 = peg$FAILED;
            }
          }
          if (s3 === peg$FAILED) {
            s3 = null;
          }
          if (s3 !== peg$FAILED) {
            s2 = [s2, s3];
            s1 = s2;
          } else {
            peg$currPos = s1;
            s1 = peg$FAILED;
          }
        } else {
          peg$currPos = s1;
          s1 = peg$FAILED;
        }
        if (s1 !== peg$FAILED) {
          peg$savedPos = s0;
          s1 = peg$c70(s1);
        }
        s0 = s1;
        return s0;
      }
      function peg$parsehcount() {
        var s0, s1, s2, s3;
        s0 = peg$currPos;
        s1 = peg$currPos;
        if (input.charCodeAt(peg$currPos) === 72) {
          s2 = peg$c71;
          peg$currPos++;
        } else {
          s2 = peg$FAILED;
          if (peg$silentFails === 0) {
            peg$fail(peg$c72);
          }
        }
        if (s2 !== peg$FAILED) {
          if (peg$c44.test(input.charAt(peg$currPos))) {
            s3 = input.charAt(peg$currPos);
            peg$currPos++;
          } else {
            s3 = peg$FAILED;
            if (peg$silentFails === 0) {
              peg$fail(peg$c45);
            }
          }
          if (s3 === peg$FAILED) {
            s3 = null;
          }
          if (s3 !== peg$FAILED) {
            s2 = [s2, s3];
            s1 = s2;
          } else {
            peg$currPos = s1;
            s1 = peg$FAILED;
          }
        } else {
          peg$currPos = s1;
          s1 = peg$FAILED;
        }
        if (s1 !== peg$FAILED) {
          peg$savedPos = s0;
          s1 = peg$c73(s1);
        }
        s0 = s1;
        return s0;
      }
      function peg$parseclass() {
        var s0, s1, s2, s3, s4, s5, s6;
        s0 = peg$currPos;
        s1 = peg$currPos;
        if (input.charCodeAt(peg$currPos) === 58) {
          s2 = peg$c74;
          peg$currPos++;
        } else {
          s2 = peg$FAILED;
          if (peg$silentFails === 0) {
            peg$fail(peg$c75);
          }
        }
        if (s2 !== peg$FAILED) {
          s3 = peg$currPos;
          if (peg$c42.test(input.charAt(peg$currPos))) {
            s4 = input.charAt(peg$currPos);
            peg$currPos++;
          } else {
            s4 = peg$FAILED;
            if (peg$silentFails === 0) {
              peg$fail(peg$c43);
            }
          }
          if (s4 !== peg$FAILED) {
            s5 = [];
            if (peg$c44.test(input.charAt(peg$currPos))) {
              s6 = input.charAt(peg$currPos);
              peg$currPos++;
            } else {
              s6 = peg$FAILED;
              if (peg$silentFails === 0) {
                peg$fail(peg$c45);
              }
            }
            while (s6 !== peg$FAILED) {
              s5.push(s6);
              if (peg$c44.test(input.charAt(peg$currPos))) {
                s6 = input.charAt(peg$currPos);
                peg$currPos++;
              } else {
                s6 = peg$FAILED;
                if (peg$silentFails === 0) {
                  peg$fail(peg$c45);
                }
              }
            }
            if (s5 !== peg$FAILED) {
              s4 = [s4, s5];
              s3 = s4;
            } else {
              peg$currPos = s3;
              s3 = peg$FAILED;
            }
          } else {
            peg$currPos = s3;
            s3 = peg$FAILED;
          }
          if (s3 === peg$FAILED) {
            if (peg$c76.test(input.charAt(peg$currPos))) {
              s3 = input.charAt(peg$currPos);
              peg$currPos++;
            } else {
              s3 = peg$FAILED;
              if (peg$silentFails === 0) {
                peg$fail(peg$c77);
              }
            }
          }
          if (s3 !== peg$FAILED) {
            s2 = [s2, s3];
            s1 = s2;
          } else {
            peg$currPos = s1;
            s1 = peg$FAILED;
          }
        } else {
          peg$currPos = s1;
          s1 = peg$FAILED;
        }
        if (s1 !== peg$FAILED) {
          peg$savedPos = s0;
          s1 = peg$c78(s1);
        }
        s0 = s1;
        return s0;
      }
      function peg$parseisotope() {
        var s0, s1, s2, s3, s4;
        s0 = peg$currPos;
        s1 = peg$currPos;
        if (peg$c42.test(input.charAt(peg$currPos))) {
          s2 = input.charAt(peg$currPos);
          peg$currPos++;
        } else {
          s2 = peg$FAILED;
          if (peg$silentFails === 0) {
            peg$fail(peg$c43);
          }
        }
        if (s2 !== peg$FAILED) {
          if (peg$c44.test(input.charAt(peg$currPos))) {
            s3 = input.charAt(peg$currPos);
            peg$currPos++;
          } else {
            s3 = peg$FAILED;
            if (peg$silentFails === 0) {
              peg$fail(peg$c45);
            }
          }
          if (s3 === peg$FAILED) {
            s3 = null;
          }
          if (s3 !== peg$FAILED) {
            if (peg$c44.test(input.charAt(peg$currPos))) {
              s4 = input.charAt(peg$currPos);
              peg$currPos++;
            } else {
              s4 = peg$FAILED;
              if (peg$silentFails === 0) {
                peg$fail(peg$c45);
              }
            }
            if (s4 === peg$FAILED) {
              s4 = null;
            }
            if (s4 !== peg$FAILED) {
              s2 = [s2, s3, s4];
              s1 = s2;
            } else {
              peg$currPos = s1;
              s1 = peg$FAILED;
            }
          } else {
            peg$currPos = s1;
            s1 = peg$FAILED;
          }
        } else {
          peg$currPos = s1;
          s1 = peg$FAILED;
        }
        if (s1 !== peg$FAILED) {
          peg$savedPos = s0;
          s1 = peg$c79(s1);
        }
        s0 = s1;
        return s0;
      }
      peg$result = peg$startRuleFunction();
      if (peg$result !== peg$FAILED && peg$currPos === input.length) {
        return peg$result;
      } else {
        if (peg$result !== peg$FAILED && peg$currPos < input.length) {
          peg$fail(peg$endExpectation());
        }
        throw peg$buildStructuredError(
          peg$maxFailExpected,
          peg$maxFailPos < input.length ? input.charAt(peg$maxFailPos) : null,
          peg$maxFailPos < input.length ? peg$computeLocation(peg$maxFailPos, peg$maxFailPos + 1) : peg$computeLocation(peg$maxFailPos, peg$maxFailPos)
        );
      }
    }
    return {
      SyntaxError: peg$SyntaxError,
      parse: peg$parse
    };
  })();

  // node_modules/smiles-drawer/src/FormulaToCommonName.js
  var FormulaToCommonName_default = {
    C2H4O2: "acetic acid",
    C3H6O: "acetone",
    C2H3N: "acetonitrile",
    C6H6: "benzene",
    CCl4: "carbon tetrachloride",
    C6H5Cl: "chlorobenzene",
    CHCl3: "chloroform",
    C6H12: "cyclohexane",
    C2H4Cl2: "1,2-dichloroethane",
    C4H10O3: "diethylene glycol",
    C6H14O3: "diglyme",
    C4H10O2: "DME",
    C3H7NO: "DMF",
    C2H6OS: "DMSO",
    C2H6O: "ethanol",
    C2H6O2: "ethylene glycol",
    C3H8O3: "glycerin",
    C7H16: "heptane",
    C6H18N3OP: "HMPA",
    C6H18N3P: "HMPT",
    C6H14: "hexane",
    CH4O: "methanol",
    C5H12O: "MTBE",
    CH2Cl2: "methylene chloride",
    CH5H9NO: "NMP",
    CH3NO2: "nitromethane",
    C5H12: "pentane",
    C5H5N: "pyridine",
    C7H8: "toluene",
    C6H15N: "triethyl amine",
    H2O: "water"
  };

  // node_modules/smiles-drawer/src/ReactionDrawer.js
  var ReactionDrawer = class {
    /**
     * The constructor for the class ReactionDrawer.
     *
     * @param {Object} options An object containing reaction drawing specitic options.
     * @param {Object} moleculeOptions An object containing molecule drawing specific options.
     */
    constructor(options, moleculeOptions) {
      this.defaultOptions = {
        scale: moleculeOptions.scale > 0 ? moleculeOptions.scale : 1,
        fontSize: moleculeOptions.fontSizeLarge * 0.8,
        fontFamily: "Arial, Helvetica, sans-serif",
        spacing: 10,
        plus: {
          size: 9,
          thickness: 1
        },
        arrow: {
          length: moleculeOptions.bondLength * 4,
          headSize: 6,
          thickness: 1,
          margin: 3
        },
        weights: {
          normalize: false
        }
      };
      this.opts = Options.extend(true, this.defaultOptions, options);
      this.drawer = new SvgDrawer(moleculeOptions);
      this.molOpts = this.drawer.opts;
    }
    /**
    * Draws the parsed reaction smiles data to a canvas element.
    *
    * @param {Object} reaction The reaction object returned by the reaction smiles parser.
    * @param {(String|SVGElement)} target The id of the HTML canvas element the structure is drawn to - or the element itself.
    * @param {String} themeName='dark' The name of the theme to use. Built-in themes are 'light' and 'dark'.
    * @param {?Object} weights=null The weights for reactants, agents, and products.
    * @param {String} textAbove='{reagents}' The text above the arrow.
    * @param {String} textBelow='' The text below the arrow.
    * @param {?Object} weights=null The weights for reactants, agents, and products.
    * @param {Boolean} infoOnly=false Only output info on the molecule without drawing anything to the canvas.
    *
    * @returns {SVGElement} The svg element
    */
    draw(reaction, target, themeName = "light", weights = null, textAbove = "{reagents}", textBelow = "", infoOnly = false) {
      this.themeManager = new ThemeManager(this.molOpts.themes, themeName);
      if (this.opts.weights.normalize) {
        let max5 = -Number.MAX_SAFE_INTEGER;
        let min5 = Number.MAX_SAFE_INTEGER;
        if ("reactants" in weights) {
          for (let i = 0; i < weights.reactants.length; i++) {
            for (let j = 0; j < weights.reactants[i].length; j++) {
              if (weights.reactants[i][j] < min5) {
                min5 = weights.reactants[i][j];
              }
              if (weights.reactants[i][j] > max5) {
                max5 = weights.reactants[i][j];
              }
            }
          }
        }
        if ("reagents" in weights) {
          for (let i = 0; i < weights.reagents.length; i++) {
            for (let j = 0; j < weights.reagents[i].length; j++) {
              if (weights.reagents[i][j] < min5) {
                min5 = weights.reagents[i][j];
              }
              if (weights.reagents[i][j] > max5) {
                max5 = weights.reagents[i][j];
              }
            }
          }
        }
        if ("products" in weights) {
          for (let i = 0; i < weights.products.length; i++) {
            for (let j = 0; j < weights.products[i].length; j++) {
              if (weights.products[i][j] < min5) {
                min5 = weights.products[i][j];
              }
              if (weights.products[i][j] > max5) {
                max5 = weights.products[i][j];
              }
            }
          }
        }
        let abs_max = Math.max(Math.abs(min5), Math.abs(max5));
        if (abs_max === 0) {
          abs_max = 1;
        }
        if ("reactants" in weights) {
          for (let i = 0; i < weights.reactants.length; i++) {
            for (let j = 0; j < weights.reactants[i].length; j++) {
              weights.reactants[i][j] /= abs_max;
            }
          }
        }
        if ("reagents" in weights) {
          for (let i = 0; i < weights.reagents.length; i++) {
            for (let j = 0; j < weights.reagents[i].length; j++) {
              weights.reagents[i][j] /= abs_max;
            }
          }
        }
        if ("products" in weights) {
          for (let i = 0; i < weights.products.length; i++) {
            for (let j = 0; j < weights.products[i].length; j++) {
              weights.products[i][j] /= abs_max;
            }
          }
        }
      }
      let svg = null;
      if (target === null || target === "svg") {
        svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        svg.setAttribute("xmlns", "http://www.w3.org/2000/svg");
        svg.setAttributeNS(null, "width", "500");
        svg.setAttributeNS(null, "height", "500");
      } else if (typeof target === "string" || target instanceof String) {
        svg = document.getElementById(target);
      } else {
        svg = target;
      }
      while (svg.firstChild) {
        svg.removeChild(svg.firstChild);
      }
      let elements = [];
      let maxHeight = 0;
      for (let i = 0; i < reaction.reactants.length; i++) {
        if (i > 0) {
          elements.push({
            width: this.opts.plus.size * this.opts.scale,
            height: this.opts.plus.size * this.opts.scale,
            svg: this.getPlus()
          });
        }
        let reactantWeights = null;
        if (weights && "reactants" in weights && weights.reactants.length > i) {
          reactantWeights = weights.reactants[i];
        }
        let reactantSvg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        this.drawer.draw(reaction.reactants[i], reactantSvg, themeName, reactantWeights, infoOnly, [], this.opts.weights.normalize);
        let element = {
          width: reactantSvg.viewBox.baseVal.width * this.opts.scale,
          height: reactantSvg.viewBox.baseVal.height * this.opts.scale,
          svg: reactantSvg
        };
        elements.push(element);
        if (element.height > maxHeight) {
          maxHeight = element.height;
        }
      }
      elements.push({
        width: this.opts.arrow.length * this.opts.scale,
        height: this.opts.arrow.headSize * this.opts.scale * 2,
        svg: this.getArrow()
      });
      let reagentsText = "";
      for (let i = 0; i < reaction.reagents.length; i++) {
        if (i > 0) {
          reagentsText += ", ";
        }
        let text = this.drawer.getMolecularFormula(reaction.reagents[i]);
        if (text in FormulaToCommonName_default) {
          text = FormulaToCommonName_default[text];
        }
        reagentsText += SvgWrapper.replaceNumbersWithSubscript(text);
      }
      textAbove = textAbove.replace("{reagents}", reagentsText);
      const topText = SvgWrapper.writeText(
        textAbove,
        this.themeManager,
        this.opts.fontSize * this.opts.scale,
        this.opts.fontFamily,
        this.opts.arrow.length * this.opts.scale
      );
      let centerOffsetX = (this.opts.arrow.length * this.opts.scale - topText.width) / 2;
      elements.push({
        svg: topText.svg,
        height: topText.height,
        width: this.opts.arrow.length * this.opts.scale,
        offsetX: -(this.opts.arrow.length * this.opts.scale + this.opts.spacing) + centerOffsetX,
        offsetY: -(topText.height / 2) - this.opts.arrow.margin,
        position: "relative"
      });
      const bottomText = SvgWrapper.writeText(
        textBelow,
        this.themeManager,
        this.opts.fontSize * this.opts.scale,
        this.opts.fontFamily,
        this.opts.arrow.length * this.opts.scale
      );
      centerOffsetX = (this.opts.arrow.length * this.opts.scale - bottomText.width) / 2;
      elements.push({
        svg: bottomText.svg,
        height: bottomText.height,
        width: this.opts.arrow.length * this.opts.scale,
        offsetX: -(this.opts.arrow.length * this.opts.scale + this.opts.spacing) + centerOffsetX,
        offsetY: bottomText.height / 2 + this.opts.arrow.margin,
        position: "relative"
      });
      for (let i = 0; i < reaction.products.length; i++) {
        if (i > 0) {
          elements.push({
            width: this.opts.plus.size * this.opts.scale,
            height: this.opts.plus.size * this.opts.scale,
            svg: this.getPlus()
          });
        }
        let productWeights = null;
        if (weights && "products" in weights && weights.products.length > i) {
          productWeights = weights.products[i];
        }
        let productSvg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        this.drawer.draw(reaction.products[i], productSvg, themeName, productWeights, infoOnly, [], this.opts.weights.normalize);
        let element = {
          width: productSvg.viewBox.baseVal.width * this.opts.scale,
          height: productSvg.viewBox.baseVal.height * this.opts.scale,
          svg: productSvg
        };
        elements.push(element);
        if (element.height > maxHeight) {
          maxHeight = element.height;
        }
      }
      let totalWidth = 0;
      elements.forEach((element) => {
        let offsetX = element.offsetX || 0;
        let offsetY = element.offsetY || 0;
        element.svg.setAttributeNS(null, "x", Math.round(totalWidth + offsetX));
        element.svg.setAttributeNS(null, "y", Math.round((maxHeight - element.height) / 2 + offsetY));
        element.svg.setAttributeNS(null, "width", Math.round(element.width));
        element.svg.setAttributeNS(null, "height", Math.round(element.height));
        svg.appendChild(element.svg);
        if (element.position !== "relative") {
          totalWidth += Math.round(element.width + this.opts.spacing + offsetX);
        }
      });
      svg.setAttributeNS(null, "viewBox", `0 0 ${totalWidth} ${maxHeight}`);
      svg.style.width = totalWidth + "px";
      svg.style.height = maxHeight + "px";
      return svg;
    }
    getPlus() {
      let s = this.opts.plus.size;
      let w = this.opts.plus.thickness;
      let svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      let rect_h = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      let rect_v = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      svg.setAttributeNS(null, "id", "plus");
      rect_h.setAttributeNS(null, "x", 0);
      rect_h.setAttributeNS(null, "y", s / 2 - w / 2);
      rect_h.setAttributeNS(null, "width", s);
      rect_h.setAttributeNS(null, "height", w);
      rect_h.setAttributeNS(null, "fill", this.themeManager.getColor("C"));
      rect_v.setAttributeNS(null, "x", s / 2 - w / 2);
      rect_v.setAttributeNS(null, "y", 0);
      rect_v.setAttributeNS(null, "width", w);
      rect_v.setAttributeNS(null, "height", s);
      rect_v.setAttributeNS(null, "fill", this.themeManager.getColor("C"));
      svg.appendChild(rect_h);
      svg.appendChild(rect_v);
      svg.setAttributeNS(null, "viewBox", `0 0 ${s} ${s}`);
      return svg;
    }
    getArrowhead() {
      let s = this.opts.arrow.headSize;
      let marker = document.createElementNS("http://www.w3.org/2000/svg", "marker");
      let polygon = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
      marker.setAttributeNS(null, "id", "arrowhead");
      marker.setAttributeNS(null, "viewBox", `0 0 ${s} ${s}`);
      marker.setAttributeNS(null, "markerUnits", "userSpaceOnUse");
      marker.setAttributeNS(null, "markerWidth", s);
      marker.setAttributeNS(null, "markerHeight", s);
      marker.setAttributeNS(null, "refX", 0);
      marker.setAttributeNS(null, "refY", s / 2);
      marker.setAttributeNS(null, "orient", "auto");
      marker.setAttributeNS(null, "fill", this.themeManager.getColor("C"));
      polygon.setAttributeNS(null, "points", `0 0, ${s} ${s / 2}, 0 ${s}`);
      marker.appendChild(polygon);
      return marker;
    }
    getCDArrowhead() {
      let s = this.opts.arrow.headSize;
      let sw = s * (7 / 4.5);
      let marker = document.createElementNS("http://www.w3.org/2000/svg", "marker");
      let path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      marker.setAttributeNS(null, "id", "arrowhead");
      marker.setAttributeNS(null, "viewBox", `0 0 ${sw} ${s}`);
      marker.setAttributeNS(null, "markerUnits", "userSpaceOnUse");
      marker.setAttributeNS(null, "markerWidth", sw * 2);
      marker.setAttributeNS(null, "markerHeight", s * 2);
      marker.setAttributeNS(null, "refX", 2.2);
      marker.setAttributeNS(null, "refY", 2.2);
      marker.setAttributeNS(null, "orient", "auto");
      marker.setAttributeNS(null, "fill", this.themeManager.getColor("C"));
      path.setAttributeNS(null, "style", "fill-rule:nonzero;");
      path.setAttributeNS(null, "d", "m 0 0 l 7 2.25 l -7 2.25 c 0 0 0.735 -1.084 0.735 -2.28 c 0 -1.196 -0.735 -2.22 -0.735 -2.22 z");
      marker.appendChild(path);
      return marker;
    }
    getArrow() {
      let s = this.opts.arrow.headSize;
      let l = this.opts.arrow.length;
      let svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      let defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
      let line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      defs.appendChild(this.getCDArrowhead());
      svg.appendChild(defs);
      svg.setAttributeNS(null, "id", "arrow");
      line.setAttributeNS(null, "x1", 0);
      line.setAttributeNS(null, "y1", -this.opts.arrow.thickness / 2);
      line.setAttributeNS(null, "x2", l);
      line.setAttributeNS(null, "y2", -this.opts.arrow.thickness / 2);
      line.setAttributeNS(null, "stroke-width", this.opts.arrow.thickness);
      line.setAttributeNS(null, "stroke", this.themeManager.getColor("C"));
      line.setAttributeNS(null, "marker-end", "url(#arrowhead)");
      svg.appendChild(line);
      svg.setAttributeNS(null, "viewBox", `0 ${-s / 2} ${l + s * (7 / 4.5)} ${s}`);
      return svg;
    }
  };

  // node_modules/smiles-drawer/src/Reaction.js
  var Reaction = class {
    /**
     * The constructor for the class Reaction.
     *
     * @param {string} reactionSmiles A reaction SMILES.
     */
    constructor(reactionSmiles) {
      this.reactantsSmiles = [];
      this.reagentsSmiles = [];
      this.productsSmiles = [];
      this.reactantsWeights = [];
      this.reagentsWeights = [];
      this.productsWeights = [];
      this.reactants = [];
      this.reagents = [];
      this.products = [];
      let parts = reactionSmiles.split(">");
      if (parts.length !== 3) {
        throw new Error('Invalid reaction SMILES: Expected exactly two ">" symbols.');
      }
      if (parts[0] !== "") {
        this.reactantsSmiles = parts[0].split(".");
      }
      if (parts[1] !== "") {
        this.reagentsSmiles = parts[1].split(".");
      }
      if (parts[2] !== "") {
        this.productsSmiles = parts[2].split(".");
      }
      for (let i = 0; i < this.reactantsSmiles.length; i++) {
        this.reactants.push(Parser_default.parse(this.reactantsSmiles[i]));
      }
      for (let i = 0; i < this.reagentsSmiles.length; i++) {
        this.reagents.push(Parser_default.parse(this.reagentsSmiles[i]));
      }
      for (let i = 0; i < this.productsSmiles.length; i++) {
        this.products.push(Parser_default.parse(this.productsSmiles[i]));
      }
    }
  };

  // node_modules/smiles-drawer/src/ReactionParser.js
  var ReactionParser = class {
    /**
     * Returns the hex code of a color associated with a key from the current theme.
     *
     * @param {String} reactionSmiles A reaction SMILES.
     * @returns {Reaction} A reaction object.
     */
    static parse(reactionSmiles) {
      let reaction = new Reaction(reactionSmiles);
      return reaction;
    }
  };

  // node_modules/smiles-drawer/src/SmilesDrawer.js
  var SmilesDrawer = class _SmilesDrawer {
    constructor(moleculeOptions = {}, reactionOptions = {}) {
      this.drawer = new SvgDrawer(moleculeOptions);
      this.reactionDrawer = new ReactionDrawer(reactionOptions, JSON.parse(JSON.stringify(this.drawer.opts)));
    }
    static apply(moleculeOptions = {}, reactionOptions = {}, attribute = "data-smiles", theme = "light", successCallback = null, errorCallback = null) {
      const drawer = new _SmilesDrawer(moleculeOptions, reactionOptions);
      drawer.apply(attribute, theme, successCallback, errorCallback);
    }
    apply(attribute = "data-smiles", theme = "light", successCallback = null, errorCallback = null) {
      let elements = document.querySelectorAll(`[${attribute}]`);
      elements.forEach((element) => {
        let smiles = element.getAttribute(attribute);
        if (smiles === null) {
          throw Error("No SMILES provided.");
        }
        let currentTheme = theme;
        let weights = null;
        if (element.hasAttribute("data-smiles-theme")) {
          currentTheme = element.getAttribute("data-smiles-theme");
        }
        if (element.hasAttribute("data-smiles-weights")) {
          weights = element.getAttribute("data-smiles-weights").split(",").map(parseFloat);
        }
        if (element.hasAttribute("data-smiles-reactant-weights") || element.hasAttribute("data-smiles-reagent-weights") || element.hasAttribute("data-smiles-product-weights")) {
          weights = { reactants: [], reagents: [], products: [] };
          if (element.hasAttribute("data-smiles-reactant-weights")) {
            weights.reactants = element.getAttribute("data-smiles-reactant-weights").split(";").map((v) => {
              return v.split(",").map(parseFloat);
            });
          }
          if (element.hasAttribute("data-smiles-reagent-weights")) {
            weights.reagents = element.getAttribute("data-smiles-reagent-weights").split(";").map((v) => {
              return v.split(",").map(parseFloat);
            });
          }
          if (element.hasAttribute("data-smiles-product-weights")) {
            weights.products = element.getAttribute("data-smiles-product-weights").split(";").map((v) => {
              return v.split(",").map(parseFloat);
            });
          }
        }
        if (element.hasAttribute("data-smiles-options") || element.hasAttribute("data-smiles-reaction-options")) {
          let moleculeOptions = {};
          if (element.hasAttribute("data-smiles-options")) {
            moleculeOptions = JSON.parse(element.getAttribute("data-smiles-options").replace(/'/g, '"'));
          }
          let reactionOptions = {};
          if (element.hasAttribute("data-smiles-reaction-options")) {
            reactionOptions = JSON.parse(element.getAttribute("data-smiles-reaction-options").replace(/'/g, '"'));
          }
          let smilesDrawer = new _SmilesDrawer(moleculeOptions, reactionOptions);
          smilesDrawer.draw(smiles, element, currentTheme, successCallback, errorCallback, weights);
        } else {
          this.draw(smiles, element, currentTheme, successCallback, errorCallback, weights);
        }
      });
    }
    /**
     * Draw the smiles to the target.
     * @param {String} smiles The SMILES to be depicted.
     * @param {*} target The target element.
     * @param {String} theme The theme.
     * @param {?CallableFunction} successCallback The function called on success.
     * @param {?CallableFunction} errorCallback The function called on error.
     * @param {?Number[]|Object} weights The weights for the gaussians.
     */
    draw(smiles, target, theme = "light", successCallback = null, errorCallback = null, weights = null) {
      let rest = [];
      [smiles, ...rest] = smiles.split(" ");
      let info = rest.join(" ");
      let settings = {};
      if (info.includes("__")) {
        let settingsString = info.substring(
          info.indexOf("__") + 2,
          info.lastIndexOf("__")
        );
        settings = JSON.parse(settingsString.replace(/'/g, '"'));
      }
      let defaultSettings = {
        textAboveArrow: "{reagents}",
        textBelowArrow: ""
      };
      settings = Options.extend(true, defaultSettings, settings);
      if (smiles.includes(">")) {
        try {
          this.drawReaction(smiles, target, theme, settings, weights, successCallback);
        } catch (err) {
          if (errorCallback) {
            errorCallback(err);
          } else {
            console.error(err);
          }
        }
      } else {
        try {
          this.drawMolecule(smiles, target, theme, weights, successCallback);
        } catch (err) {
          if (errorCallback) {
            errorCallback(err);
          } else {
            console.error(err);
          }
        }
      }
    }
    drawMolecule(smiles, target, theme, weights, callback) {
      let parseTree = Parser_default.parse(smiles);
      if (target === null || target === "svg") {
        let svg = this.drawer.draw(parseTree, null, theme, weights);
        let dims = this.getDimensions(svg);
        svg.setAttributeNS(null, "width", "" + dims.w);
        svg.setAttributeNS(null, "height", "" + dims.h);
        if (callback) {
          callback(svg);
        }
      } else if (target === "canvas") {
        let canvas = this.svgToCanvas(this.drawer.draw(parseTree, null, theme, weights));
        if (callback) {
          callback(canvas);
        }
      } else if (target === "img") {
        let img = this.svgToImg(this.drawer.draw(parseTree, null, theme, weights));
        if (callback) {
          callback(img);
        }
      } else if (target instanceof HTMLImageElement) {
        this.svgToImg(this.drawer.draw(parseTree, null, theme, weights), target);
        if (callback) {
          callback(target);
        }
      } else if (target instanceof SVGElement) {
        this.drawer.draw(parseTree, target, theme, weights);
        if (callback) {
          callback(target);
        }
      } else {
        let elements = document.querySelectorAll(target);
        elements.forEach((element) => {
          let tag = element.nodeName.toLowerCase();
          if (tag === "svg") {
            this.drawer.draw(parseTree, element, theme, weights);
            if (callback) {
              callback(element);
            }
          } else if (tag === "canvas") {
            this.svgToCanvas(this.drawer.draw(parseTree, null, theme, weights), element);
            if (callback) {
              callback(element);
            }
          } else if (tag === "img") {
            this.svgToImg(this.drawer.draw(parseTree, null, theme, weights), element);
            if (callback) {
              callback(element);
            }
          }
        });
      }
    }
    drawReaction(smiles, target, theme, settings, weights, callback) {
      let reaction = ReactionParser.parse(smiles);
      if (target === null || target === "svg") {
        let svg = this.reactionDrawer.draw(reaction, null, theme);
        let dims = this.getDimensions(svg);
        svg.setAttributeNS(null, "width", "" + dims.w);
        svg.setAttributeNS(null, "height", "" + dims.h);
        if (callback) {
          callback(svg);
        }
      } else if (target === "canvas") {
        let canvas = this.svgToCanvas(this.reactionDrawer.draw(reaction, null, theme, weights, settings.textAboveArrow, settings.textBelowArrow));
        if (callback) {
          callback(canvas);
        }
      } else if (target === "img") {
        let img = this.svgToImg(this.reactionDrawer.draw(reaction, null, theme, weights, settings.textAboveArrow, settings.textBelowArrow));
        if (callback) {
          callback(img);
        }
      } else if (target instanceof HTMLImageElement) {
        this.svgToImg(this.reactionDrawer.draw(reaction, null, theme, weights, settings.textAboveArrow, settings.textBelowArrow), target);
        if (callback) {
          callback(target);
        }
      } else if (target instanceof SVGElement) {
        this.reactionDrawer.draw(reaction, target, theme, weights, settings.textAboveArrow, settings.textBelowArrow);
        if (callback) {
          callback(target);
        }
      } else {
        let elements = document.querySelectorAll(target);
        elements.forEach((element) => {
          let tag = element.nodeName.toLowerCase();
          if (tag === "svg") {
            this.reactionDrawer.draw(reaction, element, theme, weights, settings.textAboveArrow, settings.textBelowArrow);
            if (this.reactionDrawer.opts.scale <= 0) {
              element.style.width = null;
              element.style.height = null;
            }
            if (callback) {
              callback(element);
            }
          } else if (tag === "canvas") {
            this.svgToCanvas(this.reactionDrawer.draw(reaction, null, theme, weights, settings.textAboveArrow, settings.textBelowArrow), element);
            if (callback) {
              callback(element);
            }
          } else if (tag === "img") {
            this.svgToImg(this.reactionDrawer.draw(reaction, null, theme, weights, settings.textAboveArrow, settings.textBelowArrow), element);
            if (callback) {
              callback(element);
            }
          }
        });
      }
    }
    svgToCanvas(svg, canvas = null) {
      if (canvas === null) {
        canvas = document.createElement("canvas");
      }
      let dims = this.getDimensions(canvas, svg);
      SvgWrapper.svgToCanvas(svg, canvas, dims.w, dims.h);
      return canvas;
    }
    svgToImg(svg, img = null) {
      if (img === null) {
        img = document.createElement("img");
      }
      let dims = this.getDimensions(img, svg);
      SvgWrapper.svgToImg(svg, img, dims.w, dims.h);
      return img;
    }
    /**
     *
     * @param {HTMLImageElement|HTMLCanvasElement|SVGElement} element
     * @param {SVGElement} svg
     * @returns {{w: Number, h: Number}} The width and height.
     */
    getDimensions(element, svg = null) {
      let w = this.drawer.opts.width;
      let h = this.drawer.opts.height;
      if (this.drawer.opts.scale <= 0) {
        if (!(element instanceof SVGElement)) {
          if (w === null) w = element.width;
          if (h === null) h = element.height;
        }
        if (element.style.width !== "") {
          w = parseInt(element.style.width);
        }
        if (element.style.height !== "") {
          h = parseInt(element.style.height);
        }
      } else if (svg) {
        w = parseFloat(svg.style.width);
        h = parseFloat(svg.style.height);
      }
      return { w, h };
    }
  };

  // node_modules/smiles-drawer/app.js
  var SmilesDrawerNS = {
    Version: "2.2.1",
    Drawer,
    GaussDrawer,
    Parser: Parser_default,
    ReactionDrawer,
    ReactionParser,
    SmiDrawer: SmilesDrawer,
    SvgDrawer
  };
  SmilesDrawerNS.clean = function(smiles) {
    return smiles.replace(/[^A-Za-z0-9@.+\-?!()[\]{}/\\=#$:*]/g, "");
  };
  SmilesDrawerNS.apply = function(options, selector = "canvas[data-smiles]", themeName = "light", onError = null) {
    let smilesDrawer = new Drawer(options);
    let elements = document.querySelectorAll(selector);
    for (var i = 0; i < elements.length; i++) {
      let element = elements[i];
      SmilesDrawerNS.parse(element.getAttribute("data-smiles"), function(tree) {
        smilesDrawer.draw(tree, element, themeName, false);
      }, function(err) {
        if (onError) {
          onError(err);
        }
      });
    }
  };
  SmilesDrawerNS.parse = function(smiles, successCallback, errorCallback) {
    try {
      if (successCallback) {
        successCallback(Parser_default.parse(smiles));
      }
    } catch (err) {
      if (errorCallback) {
        errorCallback(err);
      }
    }
  };
  SmilesDrawerNS.parseReaction = function(reactionSmiles, successCallback, errorCallback) {
    try {
      if (successCallback) {
        successCallback(ReactionParser.parse(reactionSmiles));
      }
    } catch (err) {
      if (errorCallback) {
        errorCallback(err);
      }
    }
  };
  if (!Array.prototype.fill) {
    let fill = function(value) {
      if (this == null) {
        throw new TypeError("this is null or not defined");
      }
      var O = Object(this);
      var len = O.length >>> 0;
      var start = arguments[1];
      var relativeStart = start >> 0;
      var k = relativeStart < 0 ? Math.max(len + relativeStart, 0) : Math.min(relativeStart, len);
      var end = arguments[2];
      var relativeEnd = end === void 0 ? len : end >> 0;
      var final = relativeEnd < 0 ? Math.max(len + relativeEnd, 0) : Math.min(relativeEnd, len);
      while (k < final) {
        O[k] = value;
        k++;
      }
      return O;
    };
    Object.defineProperty(Array.prototype, "fill", {
      value: fill,
      writeable: false
    });
  }
  if (typeof window !== "undefined" && window.document && window.document.createElement) {
    window.SmilesDrawer = SmilesDrawerNS;
    window.SmiDrawer = SmilesDrawer;
  }
  var app_default = SmilesDrawerNS;

  // src/components.jsx
  var import_react = __toESM(require_react(), 1);
  var import_jsx_runtime = __toESM(require_jsx_runtime(), 1);
  function FigureCard({ kicker, title, subtitle, controls, children, footer }) {
    return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", { className: "presentation-card", children: [
      /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", { className: "presentation-card__header", children: [
        /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
          /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { className: "presentation-card__kicker", children: kicker }),
          /* @__PURE__ */ (0, import_jsx_runtime.jsx)("h2", { children: title }),
          subtitle ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { className: "presentation-card__subtitle", children: subtitle }) : null
        ] }),
        controls ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { className: "presentation-card__controls", children: controls }) : null
      ] }),
      /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { className: "presentation-card__body", children }),
      footer ? /* @__PURE__ */ (0, import_jsx_runtime.jsx)("footer", { className: "presentation-card__footer", children: footer }) : null
    ] });
  }
  function FigureLegend({ items }) {
    return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { className: "figure-legend", role: "list", children: items.map((item) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { className: "figure-legend__item", role: "listitem", children: [
      /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { className: "figure-legend__swatch", style: { background: item.color } }),
      /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children: item.label })
    ] }, item.label)) });
  }
  function ToggleGroup({ label, options, value, onChange }) {
    return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { className: "toggle-group", role: "group", "aria-label": label, children: options.map((option) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(
      "button",
      {
        type: "button",
        className: `toggle-group__button${value === option.value ? " is-active" : ""}`,
        onClick: () => onChange(option.value),
        children: option.label
      },
      option.value
    )) });
  }
  function StatStrip({ items }) {
    return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { className: "stat-strip", children: items.map((item) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { className: "stat-strip__item", children: [
      /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { className: "stat-strip__value", children: item.value }),
      /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { className: "stat-strip__label", children: item.label })
    ] }, item.label)) });
  }

  // src/presentation-data.js
  var import_react2 = __toESM(require_react(), 1);
  var import_jsx_runtime2 = __toESM(require_jsx_runtime(), 1);
  var FALLBACK_PRESENTATION_DATA = {
    meta: {
      source: "fallback",
      generatedAt: null
    },
    pipeline: {
      total_rows: 120197,
      total_rows_label: "120.2k",
      solubility_rows: 101763,
      solubility_rows_label: "101.8k",
      unique_solutes: 19878,
      split_rows: { train: 104625, val: 7785, test: 7787 },
      split_rows_label: { train: "104.6k", val: "7.8k", test: "7.8k" },
      split_solubility_rows: { train: 90808, val: 5385, test: 5570 },
      split_solubility_rows_label: { train: "90.8k", val: "5.4k", test: "5.6k" },
      ratios: { train: 0.8, val: 0.1, test: 0.1 },
      missing_fraction_aux: 0.8496,
      missing_fraction_aux_label: "85.0%",
      scaffold_overlap: 0,
      scaffolds: {
        train: null,
        test: null
      },
      preview_rows: [
        {
          sample: "Paracetamol",
          solute_smiles: "CC(=O)Nc1ccc(O)\u2026",
          solvent_smiles: "CCO",
          T: "293",
          ln_x2: "-2.99",
          T_m: "442",
          dH_fus: "26.4",
          delta_hansen: "18.5/10.2/14.1",
          gamma_inf: "\u2014",
          source: "BigSolDBv2.1"
        },
        {
          sample: "1-nitronaphthalene",
          solute_smiles: "O=[N+]([O-])c1\u2026",
          solvent_smiles: "CCO",
          T: "298",
          ln_x2: "-3.59",
          T_m: "608",
          dH_fus: "\u2014",
          delta_hansen: "\u2014",
          gamma_inf: "\u2014",
          source: "BigSolDBv2.1"
        },
        {
          sample: "Ethylene glycol monoeicosate",
          solute_smiles: "CCCCCCCCCCCCCCCC\u2026",
          solvent_smiles: "CCO",
          T: "311",
          ln_x2: "-7.42",
          T_m: "\u2014",
          dH_fus: "\u2014",
          delta_hansen: "\u2014",
          gamma_inf: "\u2014",
          source: "BigSolDBv2.1"
        },
        {
          sample: "aux_only",
          solute_smiles: "O=[N+]([O-])c1\u2026",
          solvent_smiles: "O",
          T: "298",
          ln_x2: "\u2014",
          T_m: "638",
          dH_fus: "\u2014",
          delta_hansen: "\u2014",
          gamma_inf: "\u2014",
          source: "aux_only"
        }
      ]
    },
    linear_probe: {
      descriptors: [
        { name: "FractionCSP3", value: 0.93 },
        { name: "NumHDonors", value: 0.69 },
        { name: "TPSA", value: 0.65 },
        { name: "NumHAcceptors", value: 0.62 },
        { name: "MolLogP", value: 0.61 },
        { name: "NumRotatableBonds", value: 0.6 },
        { name: "RingCount", value: 0.57 },
        { name: "MolWt", value: 0.45 },
        { name: "HeavyAtomCount", value: 0.44 },
        { name: "MolMR", value: 0.42 }
      ],
      median_r2: 0.5045652389526367,
      median_r2_label: "0.505",
      total_descriptors: 208,
      counts: {
        ge_0_8: 3,
        between_0_5_and_0_8: 104,
        lt_0_5: 101
      }
    }
  };
  var PresentationDataContext = (0, import_react2.createContext)(FALLBACK_PRESENTATION_DATA);
  function PresentationDataProvider({ children }) {
    const [data, setData] = (0, import_react2.useState)(FALLBACK_PRESENTATION_DATA);
    (0, import_react2.useEffect)(() => {
      let cancelled = false;
      async function loadData() {
        try {
          const response = await fetch("../assets/data/tgnn-presentation-data.json", {
            cache: "no-store"
          });
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }
          const payload = await response.json();
          if (!cancelled) {
            setData(mergePresentationData(FALLBACK_PRESENTATION_DATA, payload));
          }
        } catch {
          if (!cancelled) {
            setData(FALLBACK_PRESENTATION_DATA);
          }
        }
      }
      loadData();
      return () => {
        cancelled = true;
      };
    }, []);
    return /* @__PURE__ */ (0, import_jsx_runtime2.jsx)(PresentationDataContext.Provider, { value: data, children });
  }
  function usePresentationData() {
    return (0, import_react2.useContext)(PresentationDataContext);
  }
  function mergePresentationData(base, payload) {
    return {
      ...base,
      ...payload,
      meta: {
        source: payload ? "manifest" : base.meta.source,
        generatedAt: payload?.generated_at ?? payload?.meta?.generatedAt ?? base.meta.generatedAt
      },
      pipeline: {
        ...base.pipeline,
        ...payload?.pipeline,
        split_rows: {
          ...base.pipeline.split_rows,
          ...payload?.pipeline?.split_rows
        },
        split_rows_label: {
          ...base.pipeline.split_rows_label,
          ...payload?.pipeline?.split_rows_label
        },
        split_solubility_rows: {
          ...base.pipeline.split_solubility_rows,
          ...payload?.pipeline?.split_solubility_rows
        },
        split_solubility_rows_label: {
          ...base.pipeline.split_solubility_rows_label,
          ...payload?.pipeline?.split_solubility_rows_label
        },
        ratios: {
          ...base.pipeline.ratios,
          ...payload?.pipeline?.ratios
        },
        scaffolds: {
          ...base.pipeline.scaffolds,
          ...payload?.pipeline?.scaffolds
        },
        preview_rows: payload?.pipeline?.preview_rows ?? base.pipeline.preview_rows
      },
      linear_probe: {
        ...base.linear_probe,
        ...payload?.linear_probe,
        counts: {
          ...base.linear_probe.counts,
          ...payload?.linear_probe?.counts
        },
        descriptors: payload?.linear_probe?.descriptors ?? base.linear_probe.descriptors
      }
    };
  }

  // src/figures.jsx
  var import_jsx_runtime3 = __toESM(require_jsx_runtime(), 1);
  var COLORS = {
    blue: "#2563EB",
    orange: "#F59E0B",
    green: "#10B981",
    red: "#EF4444",
    purple: "#8B5CF6",
    yellow: "#FBBF24",
    gray: "#6B7280",
    slate: "#475569",
    ink: "#0F172A",
    border: "#CBD5E1",
    line: "#94A3B8",
    sky: "#0EA5E9",
    mint: "#22C55E",
    amberSoft: "#FEF3C7",
    blueSoft: "#DBEAFE",
    greenSoft: "#D1FAE5",
    purpleSoft: "#EDE9FE",
    redSoft: "#FEE2E2"
  };
  var PAPER_FILL = "var(--deck-paper)";
  var PAPER_BORDER = "var(--deck-paper-border)";
  var PAPER_TEXT = "var(--deck-paper-text)";
  var PAPER_SOFT_TEXT = "var(--deck-paper-soft)";
  var DECK_TEXT = "var(--deck-text)";
  var EXAMPLE_PAIR = {
    solute: {
      name: "Paracetamol",
      role: "solute",
      smiles: "CC(=O)Nc1ccc(O)cc1"
    },
    solvent: {
      name: "Ethanol",
      role: "solvent",
      smiles: "CCO"
    }
  };
  function linePath(points) {
    return points.map(([x, y], index) => `${index === 0 ? "M" : "L"} ${x} ${y}`).join(" ");
  }
  function areaPath(topPoints, bottomPoints) {
    return `${linePath(topPoints)} ${bottomPoints.slice().reverse().map(([x, y]) => `L ${x} ${y}`).join(" ")} Z`;
  }
  function polarToCartesian(cx, cy, radius, angleDeg) {
    const angle = (angleDeg - 90) * Math.PI / 180;
    return {
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle)
    };
  }
  function TexInline({ children }) {
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "tex-inline", children: `\\(${children}\\)` });
  }
  function TexBlock({ children }) {
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "tex-block", children: `\\[${children}\\]` });
  }
  function MoleculeStructure({ smiles, className = "" }) {
    const svgRef = (0, import_react3.useRef)(null);
    (0, import_react3.useEffect)(() => {
      if (!svgRef.current) {
        return;
      }
      const drawer = new app_default.SvgDrawer({
        width: 360,
        height: 240,
        padding: 24,
        bondLength: 22,
        bondThickness: 1.2,
        atomVisualization: "default",
        isometric: false,
        compactDrawing: true,
        explicitHydrogens: false,
        terminalCarbons: false,
        fontSizeLarge: 10,
        fontSizeSmall: 6
      });
      svgRef.current.innerHTML = "";
      app_default.parse(
        smiles,
        (tree) => {
          drawer.draw(tree, svgRef.current, "light");
        },
        () => {
          if (svgRef.current) {
            svgRef.current.innerHTML = '<text x="20" y="32" fill="#64748b" font-size="16">Structure rendering failed.</text>';
          }
        }
      );
    }, [smiles]);
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("svg", { ref: svgRef, className: `molecule-svg ${className}`.trim(), viewBox: "0 0 360 240", "aria-hidden": "true" });
  }
  function MoleculeMiniCard({ role, name, smiles, compact = false }) {
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: `molecule-mini-card${compact ? " molecule-mini-card--compact" : ""}`, children: [
      /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "molecule-mini-card__meta", children: [
        /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: role }),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: name }),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("small", { children: smiles })
      ] }),
      /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "molecule-mini-card__art", children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(MoleculeStructure, { smiles, className: "molecule-mini-card__svg" }) })
    ] });
  }
  function ExamplePairStrip({ compact = false }) {
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: `example-pair-strip${compact ? " example-pair-strip--compact" : ""}`, children: [
      /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
        MoleculeMiniCard,
        {
          role: EXAMPLE_PAIR.solute.role,
          name: EXAMPLE_PAIR.solute.name,
          smiles: EXAMPLE_PAIR.solute.smiles,
          compact
        }
      ),
      /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "example-pair-strip__divider", children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "shared input pair" }) }),
      /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
        MoleculeMiniCard,
        {
          role: EXAMPLE_PAIR.solvent.role,
          name: EXAMPLE_PAIR.solvent.name,
          smiles: EXAMPLE_PAIR.solvent.smiles,
          compact
        }
      )
    ] });
  }
  function SourceIcon({ kind, color }) {
    const glyphs = {
      tube: { label: "SOL", sublabel: "DB" },
      crystal: { label: "Tm", sublabel: "\u0394H" },
      axes: { label: "HSP", sublabel: "\u03B4" },
      infinity: { label: "\u03B3\u221E", sublabel: "IDAC" }
    };
    const glyph = glyphs[kind] ?? { label: "DB", sublabel: "" };
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("svg", { viewBox: "0 0 40 40", "aria-hidden": "true", children: [
      /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("rect", { x: "3.5", y: "3.5", width: "33", height: "33", rx: "10", fill: "none", stroke: color, strokeWidth: "1.9" }),
      /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("path", { d: "M10 13.5h20", fill: "none", stroke: color, strokeOpacity: "0.22", strokeWidth: "1.6", strokeLinecap: "round" }),
      /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("path", { d: "M13 28h14", fill: "none", stroke: color, strokeOpacity: "0.18", strokeWidth: "1.5", strokeLinecap: "round" }),
      /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
        "text",
        {
          x: "20",
          y: glyph.sublabel ? "19.5" : "22",
          textAnchor: "middle",
          fill: color,
          fontSize: glyph.label.length > 3 ? "9.4" : "12",
          fontWeight: "800",
          fontFamily: "IBM Plex Sans, Inter, sans-serif",
          children: glyph.label
        }
      ),
      glyph.sublabel ? /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
        "text",
        {
          x: "20",
          y: "27.8",
          textAnchor: "middle",
          fill: color,
          fontSize: "6.2",
          fontWeight: "700",
          letterSpacing: "0.06em",
          fontFamily: "IBM Plex Sans, Inter, sans-serif",
          children: glyph.sublabel
        }
      ) : null
    ] });
  }
  function formatPercent(value, digits2 = 0) {
    if (value === null || value === void 0 || Number.isNaN(Number(value))) {
      return "\u2014";
    }
    return `${(Number(value) * 100).toFixed(digits2)}%`;
  }
  function ScaffoldPreview({ item, label, tone }) {
    if (item?.svg) {
      return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pipeline-scaffold-art", style: { "--scaffold-tone": tone }, children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { dangerouslySetInnerHTML: { __html: item.svg } }) });
    }
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pipeline-scaffold-art pipeline-scaffold-art--fallback", style: { "--scaffold-tone": tone }, children: [
      /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(SourceIcon, { kind: "crystal", color: tone }),
      /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: label })
    ] });
  }
  function Figure1DataPipeline() {
    const { pipeline } = usePresentationData();
    const sources = [
      {
        id: "bigsoldb",
        title: "BigSolDBv2.1",
        value: `~${pipeline.solubility_rows_label ?? "101.8k"} matched rows`,
        subtitle: "solute \xB7 solvent \xB7 T \xB7 ln x\u2082",
        icon: "tube",
        color: COLORS.blue,
        columns: ["solute_smiles", "solvent_smiles", "T", "ln_x2"]
      },
      {
        id: "crystal",
        title: "Bradley + NIST",
        value: "crystal priors + overrides",
        subtitle: "T_m \xB7 \u0394H_fus",
        icon: "crystal",
        color: COLORS.purple,
        columns: ["T_m", "dH_fus"]
      },
      {
        id: "hansen",
        title: "Hansen DB",
        value: "sparse solvent affinity labels",
        subtitle: "\u03B4_d \xB7 \u03B4_p \xB7 \u03B4_h",
        icon: "axes",
        color: COLORS.green,
        columns: ["delta_hansen"]
      },
      {
        id: "idac",
        title: "IDAC",
        value: "optional infinite dilution labels",
        subtitle: "\u03B3\u2082\u221E",
        icon: "infinity",
        color: COLORS.orange,
        columns: ["gamma_inf"]
      }
    ];
    const [activeSourceId, setActiveSourceId] = (0, import_react3.useState)(sources[0].id);
    const activeSource = sources.find((source) => source.id === activeSourceId) ?? sources[0];
    const rows = (pipeline.preview_rows ?? []).map((row, index) => {
      const syntheticGamma = ["0.54", "1.12", "0.08", "0.91"][index] ?? "0.37";
      return {
        ...row,
        gamma_inf: row.gamma_inf === "\u2014" ? syntheticGamma : row.gamma_inf
      };
    });
    const columns = ["solute_smiles", "solvent_smiles", "T", "ln_x2", "T_m", "dH_fus", "delta_hansen", "gamma_inf"];
    const columnLabels = {
      solute_smiles: "solute_smiles",
      solvent_smiles: "solvent_smiles",
      T: "T",
      ln_x2: "ln x\u2082",
      T_m: "T_m",
      dH_fus: "\u0394H_fus",
      delta_hansen: "\u03B4_d/p/h",
      gamma_inf: "\u03B3\u221E"
    };
    const splitRatios = pipeline.ratios ?? { train: 0.8, val: 0.1, test: 0.1 };
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
      FigureCard,
      {
        kicker: "Figure 1",
        title: "Data Pipeline",
        subtitle: "Current processed data are merged into one sparse supervision table, then scaffold-split without structural leakage.",
        footer: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
          StatStrip,
          {
            items: [
              { label: "Unified rows", value: pipeline.total_rows_label ?? "120.2k" },
              { label: "Aux cells missing", value: pipeline.missing_fraction_aux_label ?? "85.0%" },
              {
                label: "Train/Test scaffold overlap",
                value: pipeline.scaffold_overlap === 0 ? "0" : String(pipeline.scaffold_overlap ?? "\u2014")
              }
            ]
          }
        ),
        children: /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pipeline-layout pipeline-layout--reworked", children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pipeline-sources", children: sources.map((source) => /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)(
            "button",
            {
              type: "button",
              className: `pipeline-source${source.id === activeSourceId ? " is-active" : ""}`,
              style: { "--figure-accent": source.color },
              onClick: () => setActiveSourceId(source.id),
              children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "pipeline-source__icon", children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(SourceIcon, { kind: source.icon, color: source.color }) }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { className: "pipeline-source__body", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: source.title }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: source.value }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("small", { children: source.subtitle })
                ] })
              ]
            },
            source.id
          )) }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pipeline-builder pipeline-builder--expanded", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pipeline-builder__header", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "pipeline-builder__eyebrow", children: "Merge & Enrich" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("h3", { children: "DataBuilder" })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pipeline-builder__note", children: "canonical-SMILES left joins" })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pipeline-builder__flow", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "sources" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "pipeline-builder__flow-arrow", children: "\u2192" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "pipeline-builder__flow-focus", children: "solute_smiles \xB7 solvent_smiles \xB7 T" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "pipeline-builder__flow-arrow", children: "\u2192" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "sparse supervised table" })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pipeline-table pipeline-table--focus", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pipeline-builder__table-wrap", children: /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("table", { className: "pipeline-mini-table pipeline-mini-table--expanded", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("thead", { children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("tr", { children: columns.map((column) => /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                  "th",
                  {
                    className: activeSource.columns.includes(column) ? "is-highlighted" : "",
                    style: { "--cell-accent": activeSource.color },
                    children: columnLabels[column]
                  },
                  column
                )) }) }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("tbody", { children: rows.map((row, rowIndex) => /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("tr", { children: columns.map((column) => {
                  const value = row[column];
                  const isMissing = value === "\u2014";
                  const isHighlighted = activeSource.columns.includes(column);
                  return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                    "td",
                    {
                      title: String(value),
                      className: `${isMissing ? "is-missing" : ""} ${isHighlighted ? "is-highlighted" : ""}`.trim(),
                      style: { "--cell-accent": activeSource.color },
                      children: value
                    },
                    `${rowIndex}-${column}`
                  );
                }) }, `${row.sample ?? row.solute_smiles}-${rowIndex}`)) })
              ] }) }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pipeline-builder__facts", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pipeline-aside-card", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "Left-join sparsity" }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { children: [
                    formatPercent(pipeline.missing_fraction_aux, 1),
                    " of auxiliary supervision slots stay empty by design."
                  ] })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pipeline-aside-card", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "Current highlight" }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: activeSource.title }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("small", { children: "Highlighted columns are populated directly by the selected source." })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pipeline-aside-card", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "Processed split" }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { children: [
                    pipeline.split_rows_label?.train ?? "104.6k",
                    " / ",
                    pipeline.split_rows_label?.val ?? "7.8k",
                    " / ",
                    pipeline.split_rows_label?.test ?? "7.8k",
                    " rows"
                  ] }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("small", { children: "train / val / test after scaffold-aware partitioning." })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pipeline-aside-card", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "\u03B3\u221E display values" }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "Current processed scaffold split has no matched IDAC rows, so the \u03B3\u221E column is shown schematically." })
                ] })
              ] })
            ] })
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pipeline-split pipeline-split--scaffold", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pipeline-split__header", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "pipeline-builder__eyebrow", children: "Split" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("h3", { children: "Scaffold holdout" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("p", { children: "Right panel now uses real RDKit Murcko scaffolds from the current train/test split." })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "split-bar split-bar--detailed", "aria-label": "Train validation test split", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "split-bar__segment split-bar__segment--train", style: { flex: splitRatios.train ?? 0.8 }, children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "Train" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: formatPercent(splitRatios.train ?? 0.8) })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "split-bar__segment split-bar__segment--val split-bar__segment--compact", style: { flex: splitRatios.val ?? 0.1 }, children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: formatPercent(splitRatios.val ?? 0.1) }) }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "split-bar__segment split-bar__segment--test split-bar__segment--compact", style: { flex: splitRatios.test ?? 0.1 }, children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: formatPercent(splitRatios.test ?? 0.1) }) })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "split-bar__stats", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "Train rows" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: pipeline.split_rows_label?.train ?? "104.6k" })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "Val rows" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: pipeline.split_rows_label?.val ?? "7.8k" })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "Test rows" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: pipeline.split_rows_label?.test ?? "7.8k" })
              ] })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pipeline-scaffold-real", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pipeline-scaffold-real__title", children: "Real Murcko scaffolds" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pipeline-scaffold-real__grid", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pipeline-scaffold-card pipeline-scaffold-card--real", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(ScaffoldPreview, { item: pipeline.scaffolds?.train, label: "Train scaffold", tone: COLORS.blue }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "Train-only core" }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("small", { children: pipeline.scaffolds?.train?.example_name ?? "example from train split" })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pipeline-scaffold-stop pipeline-scaffold-stop--real", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("svg", { viewBox: "0 0 72 64", "aria-hidden": "true", children: [
                    /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("circle", { cx: "36", cy: "32", r: "18", fill: "none", stroke: COLORS.red, strokeWidth: "2.8" }),
                    /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("path", { d: "M26 22 46 42", fill: "none", stroke: COLORS.red, strokeWidth: "3.2", strokeLinecap: "round" }),
                    /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("path", { d: "M46 22 26 42", fill: "none", stroke: COLORS.red, strokeWidth: "3.2", strokeLinecap: "round" })
                  ] }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "no overlap" })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pipeline-scaffold-card pipeline-scaffold-card--real", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(ScaffoldPreview, { item: pipeline.scaffolds?.test, label: "Test scaffold", tone: COLORS.gray }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "Held-out core" }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("small", { children: pipeline.scaffolds?.test?.example_name ?? "example from test split" })
                ] })
              ] })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("p", { className: "figure-subnote", children: [
              "Generated at docs build time from `train.csv` and `test.csv`; scaffold overlap is currently ",
              pipeline.scaffold_overlap === 0 ? "zero" : pipeline.scaffold_overlap ?? "unknown",
              "."
            ] })
          ] })
        ] })
      }
    );
  }
  var ATOM_LOOKUP = {
    H: { chi: 2.2, vdw: 1.2, polar: 0.67 },
    C: { chi: 2.55, vdw: 1.7, polar: 1.76 },
    N: { chi: 3.04, vdw: 1.55, polar: 1.1 },
    O: { chi: 3.44, vdw: 1.52, polar: 0.8 },
    F: { chi: 3.98, vdw: 1.47, polar: 0.56 },
    P: { chi: 2.19, vdw: 1.8, polar: 3.63 },
    S: { chi: 2.58, vdw: 1.8, polar: 2.9 },
    Cl: { chi: 3.16, vdw: 1.75, polar: 2.18 },
    Br: { chi: 2.96, vdw: 1.85, polar: 3.05 },
    I: { chi: 2.66, vdw: 1.98, polar: 5.35 }
  };
  function normalizeCharge(charge) {
    if (charge === null || charge === void 0) {
      return 0;
    }
    if (typeof charge === "number") {
      return charge;
    }
    const value = Array.isArray(charge) ? charge.join("") : String(charge);
    return value.split("").reduce((sum, token) => {
      if (token === "+") {
        return sum + 1;
      }
      if (token === "-") {
        return sum - 1;
      }
      return sum;
    }, 0);
  }
  function bondOrder(edge) {
    if (edge.aromatic) {
      return 1.5;
    }
    if (edge.weight) {
      return edge.weight;
    }
    if (edge.bondType === "=") {
      return 2;
    }
    if (edge.bondType === "#") {
      return 3;
    }
    return 1;
  }
  function serializeSmilesGraph(graph) {
    const rawNodes = graph.vertices.filter((vertex) => vertex.value.element !== "H" && vertex.value.isDrawn !== false).map((vertex) => ({
      id: vertex.id,
      label: vertex.value.element,
      x: vertex.position.x,
      y: vertex.position.y,
      aromatic: Boolean(vertex.value.isPartOfAromaticRing),
      inRing: Boolean(vertex.value.rings?.length),
      rings: vertex.value.rings ?? [],
      neighbours: vertex.neighbours ?? [],
      degree: vertex.neighbours?.length ?? 0,
      formalCharge: normalizeCharge(vertex.value.bracket?.charge),
      explicitHydrogens: vertex.value.bracket?.hcount ?? null
    }));
    const nodeIds = new Set(rawNodes.map((node) => node.id));
    const minX = Math.min(...rawNodes.map((node) => node.x));
    const maxX = Math.max(...rawNodes.map((node) => node.x));
    const minY = Math.min(...rawNodes.map((node) => node.y));
    const maxY = Math.max(...rawNodes.map((node) => node.y));
    const width = 460;
    const height = 300;
    const padding = 30;
    const scale = Math.min(
      (width - padding * 2) / Math.max(1, maxX - minX),
      (height - padding * 2) / Math.max(1, maxY - minY)
    );
    const nodes = rawNodes.map((node) => ({
      ...node,
      cx: padding + (node.x - minX) * scale,
      cy: padding + (maxY - node.y) * scale,
      isHetero: node.label !== "C" && node.label !== "H"
    }));
    const nodeMap = new Map(nodes.map((node) => [node.id, node]));
    const edges = graph.edges.filter((edge) => nodeIds.has(edge.sourceId) && nodeIds.has(edge.targetId)).map((edge) => {
      const source = nodeMap.get(edge.sourceId);
      const target = nodeMap.get(edge.targetId);
      const sharedRing = source.rings.some((ringId) => target.rings.includes(ringId));
      return {
        id: edge.id,
        sourceId: edge.sourceId,
        targetId: edge.targetId,
        bondType: edge.bondType || "-",
        weight: edge.weight || 1,
        aromatic: Boolean(edge.isPartOfAromaticRing),
        conjugated: Boolean(edge.isPartOfAromaticRing || edge.bondType === "="),
        inRing: Boolean(edge.isPartOfAromaticRing || sharedRing),
        stereo: edge.wedge || "none"
      };
    });
    return {
      width,
      height,
      nodes,
      edges,
      stats: {
        atomCount: nodes.length,
        bondCount: edges.length,
        heteroCount: nodes.filter((node) => node.isHetero).length,
        ringCount: new Set(nodes.flatMap((node) => node.rings)).size
      }
    };
  }
  function inferHybridization(node, graphData) {
    const incidentEdges = graphData.edges.filter(
      (edge) => edge.sourceId === node.id || edge.targetId === node.id
    );
    if (node.aromatic || incidentEdges.some((edge) => edge.aromatic || edge.weight >= 2)) {
      return "sp\xB2";
    }
    if (incidentEdges.some((edge) => edge.weight >= 3)) {
      return "sp";
    }
    return "sp\xB3";
  }
  function inferHydrogenCount(node, graphData) {
    if (typeof node.explicitHydrogens === "number") {
      return node.explicitHydrogens;
    }
    const incidentEdges = graphData.edges.filter(
      (edge) => edge.sourceId === node.id || edge.targetId === node.id
    );
    const valenceDefaults = {
      C: node.aromatic ? 3 : 4,
      N: 3,
      O: 2,
      S: 2,
      P: 3,
      F: 1,
      Cl: 1,
      Br: 1,
      I: 1
    };
    const targetValence = valenceDefaults[node.label] ?? Math.max(1, node.degree);
    const occupied = incidentEdges.reduce((sum, edge) => sum + bondOrder(edge), 0);
    return Math.max(0, Math.round(targetValence - occupied - Math.max(0, node.formalCharge)));
  }
  function atomVector(node, graphData) {
    const props = ATOM_LOOKUP[node.label] ?? ATOM_LOOKUP.C;
    const hydrogenCount = inferHydrogenCount(node, graphData);
    return [
      node.isHetero ? 0.88 : 0.24,
      node.aromatic ? 0.82 : -0.18,
      node.degree / 4 * 0.9 - 0.2,
      node.inRing ? 0.76 : -0.28,
      Math.max(-1, Math.min(1, node.formalCharge / 2)),
      hydrogenCount / 4 * 0.9 - 0.2,
      (props.chi - 2.5) / 1.7,
      (props.polar - 1.7) / 3.9
    ];
  }
  function bondLabel(edge) {
    if (edge.aromatic) {
      return "aromatic";
    }
    if (edge.weight >= 3) {
      return "triple";
    }
    if (edge.weight >= 2) {
      return "double";
    }
    return "single";
  }
  function bondVector(edge, graphData) {
    const source = graphData.nodes.find((node) => node.id === edge.sourceId);
    const target = graphData.nodes.find((node) => node.id === edge.targetId);
    const dx = (target?.cx ?? 0) - (source?.cx ?? 0);
    const dy = (target?.cy ?? 0) - (source?.cy ?? 0);
    const distance = Math.sqrt(dx * dx + dy * dy) / 100;
    return [
      bondOrder(edge) / 3 * 0.9,
      edge.aromatic ? 0.84 : -0.16,
      edge.conjugated ? 0.72 : -0.22,
      edge.inRing ? 0.68 : -0.25,
      edge.stereo !== "none" ? 0.78 : -0.3,
      source?.isHetero ? 0.45 : -0.1,
      target?.isHetero ? 0.45 : -0.1,
      Math.max(-1, Math.min(1, distance - 1.1))
    ];
  }
  function useSmilesExplorer(smiles) {
    const [state, setState] = (0, import_react3.useState)({
      status: "loading",
      svgMarkup: "",
      graph: null,
      formula: "",
      error: ""
    });
    (0, import_react3.useEffect)(() => {
      let cancelled = false;
      setState((previous) => ({ ...previous, status: "loading", error: "" }));
      app_default.parse(
        smiles,
        (tree) => {
          try {
            const drawer = new app_default.SvgDrawer({
              width: 420,
              height: 280,
              padding: 18,
              bondLength: 24,
              bondThickness: 1.4,
              compactDrawing: true,
              explicitHydrogens: false,
              terminalCarbons: false,
              fontSizeLarge: 11,
              fontSizeSmall: 7
            });
            const svgElement = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            drawer.draw(tree, svgElement, "light");
            const graph = serializeSmilesGraph(drawer.preprocessor.graph);
            const formula = typeof drawer.getMolecularFormula === "function" ? drawer.getMolecularFormula() : "";
            if (!cancelled) {
              setState({
                status: "ready",
                svgMarkup: svgElement.outerHTML,
                graph,
                formula,
                error: ""
              });
            }
          } catch (error) {
            if (!cancelled) {
              setState({
                status: "error",
                svgMarkup: "",
                graph: null,
                formula: "",
                error: error?.message ?? "Structure rendering failed."
              });
            }
          }
        },
        (error) => {
          if (!cancelled) {
            setState({
              status: "error",
              svgMarkup: "",
              graph: null,
              formula: "",
              error: error?.message ?? "Invalid SMILES string."
            });
          }
        }
      );
      return () => {
        cancelled = true;
      };
    }, [smiles]);
    return state;
  }
  function FeatureVectorGrid({ values, accent }) {
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "feature-vector-grid", children: values.map((value, index) => /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)(
      "div",
      {
        className: "feature-vector-cell",
        style: {
          "--vector-accent": accent,
          "--vector-alpha": Math.min(1, Math.abs(value))
        },
        children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { children: [
            "z",
            index
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("strong", { children: [
            value >= 0 ? "+" : "",
            value.toFixed(2)
          ] })
        ]
      },
      `vec-${index}`
    )) });
  }
  function AtomInspector({ node, graphData }) {
    const props = ATOM_LOOKUP[node.label] ?? ATOM_LOOKUP.C;
    const vector = atomVector(node, graphData);
    const hydrogenCount = inferHydrogenCount(node, graphData);
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "feature-inspector", children: [
      /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "feature-inspector__eyebrow", children: "Selected atom" }),
      /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "feature-inspector__title", children: [
        /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: node.label }),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { children: [
          "atom #",
          node.id
        ] })
      ] }),
      /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "feature-detail-list", children: [
        /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "Hybridization" }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: inferHybridization(node, graphData) })
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "Formal charge" }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: node.formalCharge })
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "H count" }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: hydrogenCount })
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "Aromatic / ring" }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("strong", { children: [
            node.aromatic ? "yes" : "no",
            " / ",
            node.inRing ? "yes" : "no"
          ] })
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "\u03C7 (Pauling)" }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: props.chi.toFixed(2) })
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "r_vdW (\xC5)" }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: props.vdw.toFixed(2) })
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "\u03B1 (polariz.)" }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: props.polar.toFixed(2) })
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "Neighbours" }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: node.degree })
        ] })
      ] }),
      /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "feature-vector-card", children: [
        /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "feature-vector-card__title", children: "Input tensor slice (8 dims shown)" }),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(FeatureVectorGrid, { values: vector, accent: COLORS.blue })
      ] })
    ] });
  }
  function BondInspector({ edge, graphData }) {
    const vector = bondVector(edge, graphData);
    const source = graphData.nodes.find((node) => node.id === edge.sourceId);
    const target = graphData.nodes.find((node) => node.id === edge.targetId);
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "feature-inspector", children: [
      /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "feature-inspector__eyebrow", children: "Selected bond" }),
      /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "feature-inspector__title", children: [
        /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("strong", { children: [
          source?.label ?? "?",
          "#",
          edge.sourceId,
          " - ",
          target?.label ?? "?",
          "#",
          edge.targetId
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { children: [
          "bond #",
          edge.id
        ] })
      ] }),
      /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "feature-detail-list", children: [
        /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "Type" }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: bondLabel(edge) })
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "Conjugated" }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: edge.conjugated ? "yes" : "no" })
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "In ring" }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: edge.inRing ? "yes" : "no" })
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "Stereo" }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: edge.stereo })
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "Bond order" }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: bondOrder(edge).toFixed(1) })
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "Endpoints" }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("strong", { children: [
            source?.label ?? "?",
            " / ",
            target?.label ?? "?"
          ] })
        ] })
      ] }),
      /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "feature-vector-card", children: [
        /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "feature-vector-card__title", children: "Bond tensor slice (8 dims shown)" }),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(FeatureVectorGrid, { values: vector, accent: COLORS.orange })
      ] })
    ] });
  }
  function graphNodeById(graphData, nodeId) {
    return graphData?.nodes.find((node) => node.id === nodeId) ?? null;
  }
  function graphIncidentEdges(graphData, nodeId) {
    return (graphData?.edges ?? []).filter(
      (edge) => edge.sourceId === nodeId || edge.targetId === nodeId
    );
  }
  function graphOtherNodeId(edge, nodeId) {
    return edge.sourceId === nodeId ? edge.targetId : edge.sourceId;
  }
  function collectNHopNeighborhood(graphData, startId, hops = 2) {
    if (!graphData || startId === null || startId === void 0) {
      return /* @__PURE__ */ new Set();
    }
    const visited = /* @__PURE__ */ new Set([startId]);
    let frontier = /* @__PURE__ */ new Set([startId]);
    for (let hop = 0; hop < hops; hop += 1) {
      const nextFrontier = /* @__PURE__ */ new Set();
      frontier.forEach((nodeId) => {
        graphIncidentEdges(graphData, nodeId).forEach((edge) => {
          const otherId = graphOtherNodeId(edge, nodeId);
          if (!visited.has(otherId)) {
            visited.add(otherId);
            nextFrontier.add(otherId);
          }
        });
      });
      frontier = nextFrontier;
      if (!frontier.size) {
        break;
      }
    }
    return visited;
  }
  function averageVectors(vectors, size = 8) {
    if (!vectors.length) {
      return Array.from({ length: size }, () => 0);
    }
    const sums = Array.from({ length: size }, () => 0);
    vectors.forEach((vector) => {
      for (let index = 0; index < size; index += 1) {
        sums[index] += Number(vector[index] ?? 0);
      }
    });
    return sums.map((value) => value / vectors.length);
  }
  function summarizeGraphView(graphData, { maskedAtoms = [], maskedBonds = [] } = {}) {
    const maskedAtomSet = new Set(maskedAtoms);
    const maskedBondSet = new Set(maskedBonds);
    const atomSummary = averageVectors(
      (graphData?.nodes ?? []).map(
        (node) => maskedAtomSet.has(node.id) ? Array.from({ length: 8 }, () => 0) : atomVector(node, graphData)
      )
    );
    const bondSummary = averageVectors(
      (graphData?.edges ?? []).map(
        (edge) => maskedBondSet.has(edge.id) ? Array.from({ length: 8 }, () => 0) : bondVector(edge, graphData)
      )
    );
    return atomSummary.map((value, index) => value * 0.65 + bondSummary[index] * 0.35);
  }
  function findPretrainingSeedNode(graphData) {
    for (const node of graphData?.nodes ?? []) {
      if (node.label !== "C" || node.aromatic) {
        continue;
      }
      const incident = graphIncidentEdges(graphData, node.id);
      const hasDoubleO = incident.some((edge) => {
        const other = graphNodeById(graphData, graphOtherNodeId(edge, node.id));
        return bondOrder(edge) >= 2 && other?.label === "O";
      });
      const hasSingleO = incident.some((edge) => {
        const other = graphNodeById(graphData, graphOtherNodeId(edge, node.id));
        return bondOrder(edge) === 1 && other?.label === "O";
      });
      if (hasDoubleO && hasSingleO) {
        return node.id;
      }
    }
    return graphData?.nodes?.[0]?.id ?? null;
  }
  function findPretrainingBondTarget(graphData) {
    const carbonylBond = (graphData?.edges ?? []).find((edge) => {
      if (bondOrder(edge) < 2) {
        return false;
      }
      const source = graphNodeById(graphData, edge.sourceId);
      const target = graphNodeById(graphData, edge.targetId);
      return source?.label === "O" || target?.label === "O";
    });
    return carbonylBond?.id ?? graphData?.edges?.[0]?.id ?? null;
  }
  function buildPretrainingOverlay(graphData) {
    if (!graphData?.nodes?.length) {
      return null;
    }
    const seedId = findPretrainingSeedNode(graphData);
    const maskedAtomsSet = collectNHopNeighborhood(graphData, seedId, 2);
    const maskedAtoms = Array.from(maskedAtomsSet);
    const maskedBonds = graphData.edges.filter((edge) => maskedAtomsSet.has(edge.sourceId) && maskedAtomsSet.has(edge.targetId)).map((edge) => edge.id);
    const targetBondId = findPretrainingBondTarget(graphData);
    const targetBond = graphData.edges.find((edge) => edge.id === targetBondId) ?? graphData.edges[0];
    const anchorNode = graphNodeById(graphData, seedId) ?? graphData.nodes[0];
    const aromaticNodes = graphData.nodes.filter((node) => node.aromatic).map((node) => node.id);
    const heteroNodes = graphData.nodes.filter((node) => node.isHetero).map((node) => node.id);
    const aromaticEdges = graphData.edges.filter((edge) => edge.aromatic).map((edge) => edge.id);
    const lastAromaticNode = aromaticNodes.length ? aromaticNodes[aromaticNodes.length - 1] : null;
    const lastHeteroNode = heteroNodes.length ? heteroNodes[heteroNodes.length - 1] : null;
    const contrastiveAAtoms = Array.from(
      new Set([seedId, heteroNodes[0], aromaticNodes[1], aromaticNodes[3]].filter((value) => value !== null && value !== void 0))
    ).slice(0, 3);
    const contrastiveABonds = Array.from(
      new Set([targetBond?.id, aromaticEdges[0]].filter((value) => value !== null && value !== void 0))
    );
    const contrastiveBAtoms = Array.from(
      new Set([lastHeteroNode, aromaticNodes[0], lastAromaticNode].filter((value) => value !== null && value !== void 0))
    ).slice(0, 3);
    const contrastiveBBonds = Array.from(
      new Set([targetBond?.id, aromaticEdges[1], aromaticEdges[2]].filter((value) => value !== null && value !== void 0))
    ).slice(0, 2);
    return {
      seedId,
      maskedAtoms,
      maskedBonds,
      targetBondId: targetBond?.id ?? null,
      targetBondLabel: targetBond ? bondLabel(targetBond) : "single",
      targetBondAtoms: targetBond ? [
        graphNodeById(graphData, targetBond.sourceId),
        graphNodeById(graphData, targetBond.targetId)
      ].filter(Boolean) : [],
      atomSlice: atomVector(anchorNode, graphData),
      bondSlice: targetBond ? bondVector(targetBond, graphData) : Array.from({ length: 8 }, () => 0),
      graphSlice: summarizeGraphView(graphData),
      contrastiveAAtoms,
      contrastiveABonds,
      contrastiveASlice: summarizeGraphView(graphData, {
        maskedAtoms: contrastiveAAtoms,
        maskedBonds: contrastiveABonds
      }),
      contrastiveBAtoms,
      contrastiveBBonds,
      contrastiveBSlice: summarizeGraphView(graphData, {
        maskedAtoms: contrastiveBAtoms,
        maskedBonds: contrastiveBBonds
      }),
      anchorNode
    };
  }
  function offsetBondSegment(source, target, offset) {
    const dx = target.cx - source.cx;
    const dy = target.cy - source.cy;
    const length = Math.max(1, Math.hypot(dx, dy));
    const ox = -dy / length * offset;
    const oy = dx / length * offset;
    return {
      x1: source.cx + ox,
      y1: source.cy + oy,
      x2: target.cx + ox,
      y2: target.cy + oy
    };
  }
  function BondGlyph({ edge, source, target, stroke, opacity = 1, isHighlighted = false }) {
    const width = isHighlighted ? 4.8 : 3.2;
    if (edge.aromatic) {
      return /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)(import_jsx_runtime3.Fragment, { children: [
        /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
          "line",
          {
            x1: source.cx,
            y1: source.cy,
            x2: target.cx,
            y2: target.cy,
            stroke,
            strokeWidth: width,
            strokeLinecap: "round",
            opacity
          }
        ),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
          "line",
          {
            x1: source.cx,
            y1: source.cy,
            x2: target.cx,
            y2: target.cy,
            stroke: COLORS.ink,
            strokeWidth: "1.5",
            strokeLinecap: "round",
            strokeDasharray: "4 5",
            opacity: opacity * 0.55
          }
        )
      ] });
    }
    if (edge.weight >= 3) {
      return [-4, 0, 4].map((offset) => {
        const segment = offsetBondSegment(source, target, offset);
        return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
          "line",
          {
            x1: segment.x1,
            y1: segment.y1,
            x2: segment.x2,
            y2: segment.y2,
            stroke,
            strokeWidth: offset === 0 ? width : width - 1,
            strokeLinecap: "round",
            opacity
          },
          `bond-${edge.id}-${offset}`
        );
      });
    }
    if (edge.weight >= 2) {
      return [-2.6, 2.6].map((offset) => {
        const segment = offsetBondSegment(source, target, offset);
        return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
          "line",
          {
            x1: segment.x1,
            y1: segment.y1,
            x2: segment.x2,
            y2: segment.y2,
            stroke,
            strokeWidth: width - 0.7,
            strokeLinecap: "round",
            opacity
          },
          `bond-${edge.id}-${offset}`
        );
      });
    }
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
      "line",
      {
        x1: source.cx,
        y1: source.cy,
        x2: target.cx,
        y2: target.cy,
        stroke,
        strokeWidth: width,
        strokeLinecap: "round",
        opacity
      }
    );
  }
  function PretrainGraphView({
    graphData,
    accent,
    accentSoft,
    highlightedAtoms = [],
    maskedAtoms = [],
    highlightedBonds = [],
    maskedBonds = [],
    dimmedAtoms = [],
    dimmedBonds = [],
    showIndices = false,
    ariaLabel
  }) {
    if (!graphData) {
      return null;
    }
    const highlightedAtomSet = new Set(highlightedAtoms);
    const maskedAtomSet = new Set(maskedAtoms);
    const highlightedBondSet = new Set(highlightedBonds);
    const maskedBondSet = new Set(maskedBonds);
    const dimmedAtomSet = new Set(dimmedAtoms);
    const dimmedBondSet = new Set(dimmedBonds);
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)(
      "svg",
      {
        className: "pretrain-graph-svg",
        viewBox: `0 0 ${graphData.width} ${graphData.height}`,
        role: "img",
        "aria-label": ariaLabel,
        children: [
          graphData.edges.map((edge) => {
            const source = graphNodeById(graphData, edge.sourceId);
            const target = graphNodeById(graphData, edge.targetId);
            const isHighlighted = highlightedBondSet.has(edge.id);
            const isMasked = maskedBondSet.has(edge.id);
            const opacity = dimmedBondSet.has(edge.id) ? 0.18 : 1;
            const stroke = isHighlighted ? accent : isMasked ? COLORS.ink : edge.aromatic ? COLORS.sky : COLORS.line;
            return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("g", { children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
              BondGlyph,
              {
                edge,
                source,
                target,
                stroke,
                opacity,
                isHighlighted
              }
            ) }, `pretrain-edge-${edge.id}`);
          }),
          graphData.nodes.map((node) => {
            const isHighlighted = highlightedAtomSet.has(node.id);
            const isMasked = maskedAtomSet.has(node.id);
            const opacity = dimmedAtomSet.has(node.id) ? 0.22 : 1;
            const stroke = isHighlighted ? accent : node.isHetero ? COLORS.purple : node.aromatic ? COLORS.blue : COLORS.gray;
            const fill = isMasked ? COLORS.ink : isHighlighted ? accentSoft : "#FFFFFF";
            return /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("g", { opacity, children: [
              isHighlighted ? /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("circle", { cx: node.cx, cy: node.cy, r: "19", fill: "none", stroke: accent, strokeOpacity: "0.22", strokeWidth: "8" }) : null,
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                "circle",
                {
                  cx: node.cx,
                  cy: node.cy,
                  r: isHighlighted ? 15.5 : 13.8,
                  fill,
                  stroke,
                  strokeWidth: isHighlighted ? 3.8 : 2.7
                }
              ),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                "text",
                {
                  x: node.cx,
                  y: node.cy + 4.6,
                  textAnchor: "middle",
                  fontSize: "13",
                  fontWeight: "800",
                  fill: isMasked ? "#FFFFFF" : node.isHetero ? COLORS.purple : COLORS.ink,
                  children: node.label
                }
              ),
              showIndices ? /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                "text",
                {
                  x: node.cx,
                  y: node.cy - 18,
                  textAnchor: "middle",
                  fontSize: "10",
                  fontWeight: "800",
                  fill: COLORS.slate,
                  children: node.id
                }
              ) : null
            ] }, `pretrain-node-${node.id}`);
          })
        ]
      }
    );
  }
  function Figure2Featurization() {
    const defaultSmiles = "CC(=O)Nc1ccc(O)cc1";
    const [draftSmiles, setDraftSmiles] = (0, import_react3.useState)(defaultSmiles);
    const [committedSmiles, setCommittedSmiles] = (0, import_react3.useState)(defaultSmiles);
    const [selectedEntity, setSelectedEntity] = (0, import_react3.useState)({ type: "atom", id: null });
    const explorer = useSmilesExplorer(committedSmiles);
    (0, import_react3.useEffect)(() => {
      if (explorer.status !== "ready" || !explorer.graph?.nodes.length) {
        return;
      }
      const firstHetero = explorer.graph.nodes.find((node) => node.isHetero) ?? explorer.graph.nodes[0];
      setSelectedEntity({ type: "atom", id: firstHetero.id });
    }, [committedSmiles, explorer.status, explorer.graph?.nodes?.length]);
    const selectedAtom = selectedEntity.type === "atom" ? explorer.graph?.nodes.find((node) => node.id === selectedEntity.id) : null;
    const selectedBond = selectedEntity.type === "bond" ? explorer.graph?.edges.find((edge) => edge.id === selectedEntity.id) : null;
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
      FigureCard,
      {
        kicker: "Figure 2",
        title: "Molecular Featurization",
        subtitle: "The slide now uses one parsed SMILES source for both the 2D depiction and the graph, with clickable atoms and bonds on the right.",
        children: /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "featurization-rebuilt featurization-rebuilt--interactive", children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "featurization-flow", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "canonical SMILES" }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "\u2192 2D depiction" }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "\u2192 graph topology" }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "\u2192 click atom/bond to inspect tensor slice" })
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)(
            "form",
            {
              className: "smiles-input-bar",
              onSubmit: (event) => {
                event.preventDefault();
                setCommittedSmiles(draftSmiles.trim() || defaultSmiles);
              },
              children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("label", { className: "smiles-input-bar__field", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "SMILES input" }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                    "input",
                    {
                      type: "text",
                      value: draftSmiles,
                      onChange: (event) => setDraftSmiles(event.target.value),
                      spellCheck: "false"
                    }
                  )
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("button", { type: "submit", className: "pill-button pill-button--primary", children: "Render" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                  "button",
                  {
                    type: "button",
                    className: "pill-button",
                    onClick: () => {
                      setDraftSmiles(defaultSmiles);
                      setCommittedSmiles(defaultSmiles);
                    },
                    children: "Reset"
                  }
                )
              ]
            }
          ),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "featurization-panels featurization-panels--interactive", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("section", { className: "featurization-panel featurization-panel--input", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "featurization-label", children: "SMILES string" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "smiles-card smiles-card--interactive", children: committedSmiles }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "molecule-stats-grid", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: explorer.graph?.stats.atomCount ?? "\u2014" }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "atoms" })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: explorer.graph?.stats.bondCount ?? "\u2014" }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "bonds" })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: explorer.graph?.stats.ringCount ?? "\u2014" }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "rings" })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: explorer.formula || "\u2014" }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "formula" })
                ] })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("p", { className: "figure-subnote", children: "Default input is paracetamol. The same parsed graph drives both depiction and graph tensors." })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("section", { className: "featurization-panel featurization-panel--structure", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "featurization-label", children: "2D depiction" }),
              explorer.status === "error" ? /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "molecule-error", children: explorer.error }) : /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "molecule-render", dangerouslySetInnerHTML: { __html: explorer.svgMarkup } }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("p", { className: "figure-subnote", children: "Rendered automatically from the current input instead of a hand-drawn placeholder." })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("section", { className: "featurization-panel featurization-panel--graph", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "featurization-label", children: "Interactive molecular graph" }),
              explorer.status === "error" ? /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "molecule-error", children: explorer.error }) : /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "graph-explorer", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)(
                  "svg",
                  {
                    className: "graph-svg graph-svg--interactive",
                    viewBox: `0 0 ${explorer.graph?.width ?? 460} ${explorer.graph?.height ?? 300}`,
                    role: "img",
                    "aria-label": `Molecular graph for ${committedSmiles}`,
                    children: [
                      explorer.graph?.edges.map((edge) => {
                        const source = explorer.graph.nodes.find((node) => node.id === edge.sourceId);
                        const target = explorer.graph.nodes.find((node) => node.id === edge.targetId);
                        const isSelected = selectedEntity.type === "bond" && selectedEntity.id === edge.id;
                        return /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("g", { children: [
                          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                            "line",
                            {
                              x1: source.cx,
                              y1: source.cy,
                              x2: target.cx,
                              y2: target.cy,
                              stroke: isSelected ? COLORS.orange : edge.aromatic ? COLORS.blue : COLORS.line,
                              strokeWidth: isSelected ? 7 : edge.aromatic ? 4.6 : edge.weight >= 2 ? 4.2 : 3.5,
                              strokeLinecap: "round"
                            }
                          ),
                          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                            "line",
                            {
                              x1: source.cx,
                              y1: source.cy,
                              x2: target.cx,
                              y2: target.cy,
                              stroke: "transparent",
                              strokeWidth: "18",
                              strokeLinecap: "round",
                              className: "graph-hitline",
                              onClick: () => setSelectedEntity({ type: "bond", id: edge.id })
                            }
                          )
                        ] }, `edge-${edge.id}`);
                      }),
                      explorer.graph?.nodes.map((node) => {
                        const isSelected = selectedEntity.type === "atom" && selectedEntity.id === node.id;
                        return /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)(
                          "g",
                          {
                            className: "graph-node",
                            onClick: () => setSelectedEntity({ type: "atom", id: node.id }),
                            children: [
                              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                                "circle",
                                {
                                  cx: node.cx,
                                  cy: node.cy,
                                  r: isSelected ? 18 : 15,
                                  fill: isSelected ? COLORS.blueSoft : "#FFFFFF",
                                  stroke: isSelected ? COLORS.blue : node.isHetero ? COLORS.purple : COLORS.gray,
                                  strokeWidth: isSelected ? 4.2 : 3
                                }
                              ),
                              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                                "text",
                                {
                                  x: node.cx,
                                  y: node.cy + 5,
                                  textAnchor: "middle",
                                  fontSize: "15",
                                  fontWeight: "800",
                                  fill: node.isHetero ? COLORS.purple : COLORS.ink,
                                  children: node.label
                                }
                              )
                            ]
                          },
                          `node-${node.id}`
                        );
                      })
                    ]
                  }
                ),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "graph-explorer__detail", children: selectedBond ? /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(BondInspector, { edge: selectedBond, graphData: explorer.graph }) : selectedAtom ? /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(AtomInspector, { node: selectedAtom, graphData: explorer.graph }) : /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "feature-inspector feature-inspector--empty", children: "Click any atom or bond to inspect its features." }) })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("p", { className: "figure-subnote", children: "Click a node or edge on the graph to switch the inspector between atom and bond tensors." })
            ] })
          ] })
        ] })
      }
    );
  }
  function FigurePretraining() {
    const exampleSmiles = "CC(=O)Oc1ccccc1C(=O)O";
    const explorer = useSmilesExplorer(exampleSmiles);
    const graphData = explorer.graph;
    const overlay2 = buildPretrainingOverlay(graphData);
    const descriptorRows = [
      { name: "MolLogP", value: "1.31", note: "lipophilicity" },
      { name: "TPSA", value: "63.6", note: "polar surface area" },
      { name: "MolWt", value: "180.2", note: "molecular weight" },
      { name: "FractionCSP3", value: "0.11", note: "aliphatic fraction" },
      { name: "NumHAcceptors", value: "3", note: "H-bond acceptors" },
      { name: "LabuteASA", value: "74.8", note: "approx. surface area" }
    ];
    const targetBondAtomIds = overlay2?.targetBondAtoms?.map((node) => node.id) ?? [];
    const dimmedMaskAtoms = graphData?.nodes?.filter((node) => !(overlay2?.maskedAtoms ?? []).includes(node.id)).map((node) => node.id) ?? [];
    const dimmedMaskBonds = graphData?.edges?.filter((edge) => !(overlay2?.maskedBonds ?? []).includes(edge.id)).map((edge) => edge.id) ?? [];
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
      FigureCard,
      {
        kicker: "Stage 0",
        title: "Pretraining",
        subtitle: "The repository includes a standalone encoder/readout pretraining stage in `src/tgnn_solv/pretrain.py`.",
        footer: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
          StatStrip,
          {
            items: [
              { label: "Source", value: "ZINC250k" },
              { label: "Batch / LR", value: "128 / 3e-4" },
              { label: "Contrastive \u03C4", value: "0.1" }
            ]
          }
        ),
        children: /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pretrain-layout pretrain-layout--real", children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pretrain-topbar", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pretrain-meta-card", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pipeline-builder__eyebrow", children: "SMILES source" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "`download_zinc250k()`" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "ZINC250k when available, otherwise canonicalized BigSolDB SMILES fallback." })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pretrain-flow-card", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pretrain-flow-card__row", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "SMILES" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "\u2192" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "`PretrainDataset`" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "\u2192" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "shared encoder + readout" })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pretrain-flow-card__note", children: "Updates `model.gnn` and `model.readout` in place, then discards the temporary Stage 0 heads." })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pretrain-meta-card", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pipeline-builder__eyebrow", children: "Repo behavior" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "Optional, API-driven" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "`scripts/training/train.py` does not launch Stage 0 automatically; the maintained entry point is the Python API / notebook walkthrough." })
            ] })
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pretrain-overview", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("section", { className: "pretrain-overview__structure", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pretrain-task-card__eyebrow", children: "Real molecule used across all four tasks" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("strong", { children: [
                "Aspirin \xB7 ",
                exampleSmiles
              ] }),
              explorer.status === "ready" ? /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pretrain-structure-frame", dangerouslySetInnerHTML: { __html: explorer.svgMarkup } }) : /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "molecule-error", children: explorer.error || "Rendering structure\u2026" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("p", { className: "figure-subnote", children: "The same parsed SMILES drives both the 2D depiction and the graph below; the slide no longer uses hand-drawn toy nodes." })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("section", { className: "pretrain-overview__graph", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pretrain-task-card__eyebrow", children: "Structure \u2192 graph \u2192 shared encoder" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pretrain-graph-frame pretrain-graph-frame--large", children: graphData ? /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                PretrainGraphView,
                {
                  graphData,
                  accent: COLORS.blue,
                  accentSoft: COLORS.blueSoft,
                  highlightedAtoms: overlay2 ? [overlay2.seedId] : [],
                  highlightedBonds: overlay2?.targetBondId ? [overlay2.targetBondId] : [],
                  ariaLabel: "Real molecular graph used for Stage 0 pretraining tasks"
                }
              ) : /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "molecule-error", children: explorer.error || "Rendering graph\u2026" }) }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pretrain-mini-pipeline", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "SMILES" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "\u2192" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "`smiles_to_graph()`" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "\u2192" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "GNN encoder" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "\u2192" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "`h_atoms`, `g_mol`, `z`" })
              ] })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("section", { className: "pretrain-overview__vectors", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pretrain-signal-card", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pretrain-task-card__eyebrow", children: "Masked atom target slice" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: overlay2 ? `${overlay2.anchorNode.label}${overlay2.anchorNode.id}` : "atom slice" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(FeatureVectorGrid, { values: overlay2?.atomSlice ?? Array.from({ length: 8 }, () => 0), accent: COLORS.blue })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pretrain-signal-card", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pretrain-task-card__eyebrow", children: "Graph summary slice" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "`g_mol` before task heads" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(FeatureVectorGrid, { values: overlay2?.graphSlice ?? Array.from({ length: 8 }, () => 0), accent: COLORS.green })
              ] })
            ] })
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pretrain-task-grid pretrain-task-grid--real", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("section", { className: "pretrain-task-card pretrain-task-card--blue", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pretrain-task-card__title", children: "1. Masked 2-hop subgraph" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pretrain-task-card__split", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pretrain-graph-frame", children: graphData ? /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                  PretrainGraphView,
                  {
                    graphData,
                    accent: COLORS.blue,
                    accentSoft: COLORS.blueSoft,
                    highlightedAtoms: overlay2 ? [overlay2.seedId] : [],
                    maskedAtoms: overlay2?.maskedAtoms ?? [],
                    maskedBonds: overlay2?.maskedBonds ?? [],
                    dimmedAtoms: dimmedMaskAtoms,
                    dimmedBonds: dimmedMaskBonds,
                    showIndices: true,
                    ariaLabel: "Two-hop masked neighborhood on a real molecular graph"
                  }
                ) : null }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pretrain-task-card__meta", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pretrain-task-card__eyebrow", children: "`PretrainDataset._mask_subgraph()`" }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("p", { className: "figure-subnote", children: "A real carbonyl-centered neighborhood is zeroed before the encoder. The dark connected component is the 2-hop mask, not a disconnected random atom sample." }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexBlock, { children: "L_{atom} = \\|\\hat x_{mask} - x_{mask}\\|_2^2" }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pretrain-legend", children: [
                    /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { children: [
                      /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("i", { style: { background: COLORS.ink } }),
                      " masked atoms"
                    ] }),
                    /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { children: [
                      /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("i", { style: { background: COLORS.blue } }),
                      " seed / context anchor"
                    ] })
                  ] })
                ] })
              ] })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("section", { className: "pretrain-task-card pretrain-task-card--purple", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pretrain-task-card__title", children: "2. Bond type prediction" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pretrain-task-card__split", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pretrain-graph-frame", children: graphData ? /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                  PretrainGraphView,
                  {
                    graphData,
                    accent: COLORS.purple,
                    accentSoft: COLORS.purpleSoft,
                    highlightedAtoms: targetBondAtomIds,
                    highlightedBonds: overlay2?.targetBondId ? [overlay2.targetBondId] : [],
                    ariaLabel: "Real molecular bond highlighted for bond-type prediction"
                  }
                ) : null }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pretrain-task-card__meta", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pretrain-task-card__eyebrow", children: "`BondPredictionHead`" }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("p", { className: "figure-subnote", children: [
                    "The highlighted carbonyl bond is read from the parsed structure, endpoint states are concatenated as ",
                    /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "[h_u \\parallel h_v]" }),
                    ", and the head predicts one of the four bond classes stored in `edge_attr[:, :4]`."
                  ] }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pretrain-bond-classes", children: ["single", "double", "triple", "aromatic"].map((label) => /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: `pretrain-bond-class${overlay2?.targetBondLabel === label ? " is-active" : ""}`, children: label }, label)) }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexBlock, { children: "L_{bond} = \\mathrm{CE}(\\hat y_{bond}, y_{bond})" })
                ] })
              ] })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("section", { className: "pretrain-task-card pretrain-task-card--green", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pretrain-task-card__title", children: "3. RDKit property regression" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pretrain-task-card__split", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pretrain-property-structure", children: explorer.status === "ready" ? /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { dangerouslySetInnerHTML: { __html: explorer.svgMarkup } }) : /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "molecule-error", children: explorer.error || "Rendering structure\u2026" }) }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pretrain-task-card__meta", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pretrain-task-card__eyebrow", children: "Real descriptor targets from RDKit" }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pretrain-descriptor-grid", children: descriptorRows.map((row) => /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pretrain-descriptor-card", children: [
                    /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pretrain-descriptor-card__name", children: row.name }),
                    /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: row.value }),
                    /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("small", { children: row.note })
                  ] }, row.name)) }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("p", { className: "figure-subnote", children: [
                    "These are actual RDKit targets computed on the aspirin graph. The property head regresses the whole descriptor vector from the pooled representation ",
                    /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "g_{mol}" }),
                    ", so Stage 0 teaches the encoder to preserve global molecular semantics that matter for solubility."
                  ] }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexBlock, { children: "L_{prop} = \\|\\hat p - p\\|_2^2" })
                ] })
              ] })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("section", { className: "pretrain-task-card pretrain-task-card--orange", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pretrain-task-card__title", children: "4. Graph contrastive learning" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pretrain-contrastive-row", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pretrain-contrastive-view", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pretrain-task-card__eyebrow", children: "aug view 1" }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pretrain-graph-frame pretrain-graph-frame--compact", children: graphData ? /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                    PretrainGraphView,
                    {
                      graphData,
                      accent: COLORS.orange,
                      accentSoft: COLORS.amberSoft,
                      maskedAtoms: overlay2?.contrastiveAAtoms ?? [],
                      maskedBonds: overlay2?.contrastiveABonds ?? [],
                      highlightedAtoms: overlay2?.contrastiveAAtoms?.slice(0, 1) ?? [],
                      ariaLabel: "First augmented graph view for contrastive pretraining"
                    }
                  ) : null }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(FeatureVectorGrid, { values: overlay2?.contrastiveASlice ?? Array.from({ length: 8 }, () => 0), accent: COLORS.orange })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pretrain-contrastive-view", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pretrain-task-card__eyebrow", children: "aug view 2" }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "pretrain-graph-frame pretrain-graph-frame--compact", children: graphData ? /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                    PretrainGraphView,
                    {
                      graphData,
                      accent: COLORS.orange,
                      accentSoft: COLORS.amberSoft,
                      maskedAtoms: overlay2?.contrastiveBAtoms ?? [],
                      maskedBonds: overlay2?.contrastiveBBonds ?? [],
                      highlightedAtoms: overlay2?.contrastiveBAtoms?.slice(0, 1) ?? [],
                      ariaLabel: "Second augmented graph view for contrastive pretraining"
                    }
                  ) : null }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(FeatureVectorGrid, { values: overlay2?.contrastiveBSlice ?? Array.from({ length: 8 }, () => 0), accent: COLORS.orange })
                ] })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("p", { className: "figure-subnote", children: "Both views come from the same real molecule after node and edge zeroing. The graph is pooled to `g_aug`, projected to 128-d, normalized, and matched across the batch." }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexBlock, { children: "L_{ctr} = \\tfrac{1}{2}\\left[\\mathrm{CE}(z_1 z_2^\\top / \\tau, y) + \\mathrm{CE}(z_2 z_1^\\top / \\tau, y)\\right]" })
            ] })
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pretrain-loss-card", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pretrain-loss-card__main", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexBlock, { children: "L = 1.0\\,L_{atom} + 0.5\\,L_{bond} + 1.0\\,L_{prop} + 0.5\\,L_{ctr}" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("p", { className: "figure-subnote", children: "Default optimizer path in the repo: AdamW, cosine LR schedule, gradient clipping at 1.0, and Stage 0 heads removed after pretraining completes." })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "pretrain-loss-card__chips", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "`n_epochs=30`" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "`batch_size=128`" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "`mask_ratio=0.15`" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "`bond_mask_ratio=0.15`" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "`aug_node_mask_ratio=0.15`" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "`aug_edge_mask_ratio=0.15`" })
            ] })
          ] })
        ] })
      }
    );
  }
  function Figure3Architecture() {
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
      FigureCard,
      {
        kicker: "Figure 3",
        title: "TGNN-Solv Architecture",
        subtitle: "A vertical, physics-bottlenecked forward path from graphs to `ln x\u2082_final`.",
        footer: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
          FigureLegend,
          {
            items: [
              { label: "Encoding", color: "rgba(37, 99, 235, 0.70)" },
              { label: "Auxiliary heads", color: "rgba(139, 92, 246, 0.70)" },
              { label: "Interaction", color: "rgba(16, 185, 129, 0.70)" },
              { label: "Physics", color: "rgba(245, 158, 11, 0.70)" },
              { label: "Solver", color: "rgba(239, 68, 68, 0.70)" }
            ]
          }
        ),
        children: /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "architecture-rebuilt architecture-rebuilt--compact", children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("section", { className: "architecture-zone architecture-zone--blue", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "architecture-zone__title", children: "1. Molecular encoding" }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "architecture-compact-grid architecture-compact-grid--two", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "architecture-card architecture-card--label", children: "Solute graph" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "architecture-card architecture-card--label", children: "Solvent graph" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "architecture-card architecture-card--shared architecture-card--span-2", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "architecture-card__row", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
                    /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "Shared GNN encoder" }),
                    /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "6-layer MPNN with tied weights" })
                  ] }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "architecture-badge", children: "weight sharing" })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "architecture-encoding-grid", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "architecture-card architecture-card--ghost", children: "h_sol atoms" }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "architecture-card architecture-card--ghost", children: "same parameters" }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "architecture-card architecture-card--ghost", children: "h_slv atoms" })
                ] })
              ] })
            ] })
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "architecture-flow-down architecture-flow-down--between", children: "\u2193" }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("section", { className: "architecture-zone architecture-zone--purple", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "architecture-zone__title", children: "2. Pre-interaction heads" }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "architecture-compact-grid architecture-compact-grid--two", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "architecture-card", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "architecture-card__row", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "FusionHead" }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "architecture-chip architecture-chip--ghost", children: "temperature-invariant" })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { children: [
                  "Predicts ",
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "T_m,\\ \\Delta H_{fus}" })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexBlock, { children: "T_m = T_m^{GC} + 50\\tanh(h)" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("small", { children: "Bounded residual around a calibrated Joback prior." })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "architecture-card", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "architecture-card__row", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "HansenHead" }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "architecture-chip architecture-chip--ghost", children: "temperature-invariant" })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "\\delta_d,\\ \\delta_p,\\ \\delta_h" }),
                  " from solute features"
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("small", { children: "Auxiliary branch regularizes the solute representation before interaction." })
              ] })
            ] })
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "architecture-flow-down architecture-flow-down--between", children: "\u2193" }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("section", { className: "architecture-zone architecture-zone--green", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "architecture-zone__title", children: "3. Interaction & readout" }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "architecture-compact-grid architecture-compact-grid--two", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "architecture-card architecture-card--ghost", children: "h_sol atoms" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "architecture-card architecture-card--ghost", children: "h_slv atoms" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "architecture-card architecture-card--span-2", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "Cross-attention \xD73" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "Bidirectional solute \u2194 solvent context exchange." })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "architecture-card architecture-card--span-2", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "Attention + Set2Set readout" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "g_{sol}" }),
                  " and ",
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "g_{slv}" }),
                  " pooled from interacting atom states"
                ] })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "architecture-card architecture-card--ghost", children: "g_sol (3d)" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "architecture-card architecture-card--ghost", children: "g_slv (3d)" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "architecture-card architecture-card--span-2", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "Pair representation" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexBlock, { children: "g_{pair} = [g_{sol} \\parallel g_{slv} \\parallel g_{sol}\\odot g_{slv} \\parallel |g_{sol}-g_{slv}|]" })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "architecture-card architecture-card--optional architecture-card--span-2", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "Optional descriptor augmentation" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { children: [
                  "Descriptors \u2192 normalize \u2192 MLP \u2192 concatenate to ",
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "g_{pair}" })
                ] })
              ] })
            ] })
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "architecture-flow-down architecture-flow-down--between", children: "\u2193" }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("section", { className: "architecture-zone architecture-zone--orange", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "architecture-zone__title", children: "4. Physics heads" }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "architecture-compact-grid architecture-compact-grid--three", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "architecture-card architecture-card--ghost", children: "pair embedding + temperature" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "architecture-card architecture-card--ghost", children: "thermometer injection" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "architecture-card", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "NRTLHead" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "\\tau_{12}(T),\\ \\tau_{21}(T),\\ \\alpha" }) })
              ] })
            ] })
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "architecture-flow-down architecture-flow-down--between", children: "\u2193" }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("section", { className: "architecture-zone architecture-zone--red", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "architecture-zone__title", children: "5. SLE solver & correction" }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "architecture-compact-grid architecture-compact-grid--two", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "architecture-card architecture-card--solver", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "architecture-card__row", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "Hardcoded SLE solver" }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "architecture-badge architecture-badge--solver", children: "0 learnable params" })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexBlock, { children: "\\Phi(T)=\\frac{\\Delta H}{R}\\left(\\frac{1}{T}-\\frac{1}{T_m}\\right)-\\Delta C_p\\,\\psi(T)" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "solver-loop", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "x_2^{(0)} = \\exp(-\\Phi)" }) }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "\\ln \\gamma_2 = \\mathrm{NRTL}(x_1,x_2,\\tau,\\alpha)" }) }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "x_2^{(k+1)} = \\lambda e^{-\\Phi-\\ln\\gamma_2} + (1-\\lambda)x_2^{(k)}" }) })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexBlock, { children: "\\frac{d x_2^*}{d\\theta} = -\\frac{\\partial(\\Phi + \\ln\\gamma_2)/\\partial\\theta}{1 + x_2^*\\eta}" })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "architecture-card", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "Bounded correction" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexBlock, { children: "\\delta\\theta: \\{T_m,\\ \\Delta H,\\ \\tau\\}" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexBlock, { children: "\\ln x_{2,final} = \\ln x_{2,physics} + (1-gate)\\,\\mathrm{clip}(\\Delta)" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "Residual correction stays in parameter space instead of bypassing the solver." })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "architecture-card architecture-card--final architecture-card--span-2", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "\\ln x_{2,final}" }) }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "Physics-guided prediction with bounded correction." })
              ] })
            ] })
          ] })
        ] })
      }
    );
  }
  function Figure3ABaseline() {
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
      FigureCard,
      {
        kicker: "Figure 3A",
        title: "Matched Baseline",
        subtitle: "TGNN-Solv and DirectGNN share the same upstream chemistry stack; the maintained comparison isolates the physics bottleneck itself.",
        footer: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
          StatStrip,
          {
            items: [
              { label: "Shared encoder", value: "same GNN" },
              { label: "Shared interaction", value: "same cross-attn" },
              { label: "Different head", value: "physics vs direct" }
            ]
          }
        ),
        children: /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "baseline-slide", children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(ExamplePairStrip, { compact: true }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("section", { className: "baseline-shared", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "baseline-shared__header", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "pipeline-builder__eyebrow", children: "Controlled comparison" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("h3", { children: "Everything upstream is matched" })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("small", { children: "Fair ablation of the physics path, not a completely different backbone." })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "baseline-shared__flow", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "baseline-chip baseline-chip--shared", children: "Shared GNN encoder" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "baseline-arrow", children: "\u2192" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "baseline-chip baseline-chip--shared", children: "Cross-attention / interaction" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "baseline-arrow", children: "\u2192" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "baseline-chip baseline-chip--shared", children: "PhysicsAwareReadout" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "baseline-arrow", children: "\u2192" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "baseline-chip baseline-chip--shared", children: "pair representation" })
            ] })
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "baseline-branches", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("section", { className: "baseline-lane baseline-lane--physics", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "baseline-lane__header", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "TGNN-Solv" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "baseline-lane__badge baseline-lane__badge--physics", children: "physics bottleneck" })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "baseline-lane__stack", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "baseline-chip", children: [
                  "FusionHead \u2192 ",
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "T_m,\\ \\Delta H_{fus},\\ \\Delta C_p" })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "baseline-chip", children: [
                  "NRTLHead \u2192 ",
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "\\tau_{12}(T),\\ \\tau_{21}(T),\\ \\alpha" })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "baseline-chip", children: "Hardcoded SLE solver + bounded correction" })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexBlock, { children: "\\ln x_{2,final} = \\mathrm{SLE}(\\theta_{pred}) + (1-gate)\\,\\mathrm{clip}(\\Delta)" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "baseline-lane__notes", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { children: "Pros: extrapolation, interpretable intermediates, thermodynamic structure." }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { children: "Constraint: representation errors are filtered through the solver-facing parameterization." })
              ] })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("section", { className: "baseline-lane baseline-lane--direct", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "baseline-lane__header", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "DirectGNN" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "baseline-lane__badge baseline-lane__badge--direct", children: "no explicit physics" })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "baseline-lane__stack", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "baseline-chip", children: "thermometer temperature encoding" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "baseline-chip", children: [
                  "direct MLP \u2192 ",
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "\\ln x_2" })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "baseline-chip", children: "optional Morgan / descriptor augmentation" })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexBlock, { children: "\\ln x_2 = \\mathrm{MLP}\\big([g_{pair} \\parallel \\mathrm{temp}(T)]\\big)" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "baseline-lane__notes", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { children: "Pros: simpler head, fewer structured constraints, easy descriptor fusion." }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
                  "Removes ",
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("code", { children: "FusionHead" }),
                  ", ",
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("code", { children: "NRTLHead" }),
                  ", ",
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("code", { children: "SLESolver" }),
                  ", and ",
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("code", { children: "AdaptivePhysicsCorrection" }),
                  "."
                ] })
              ] })
            ] })
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "baseline-summary-grid", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "baseline-summary-card", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "Same chemistry frontend" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "The experiment holds graph encoding, interaction, and readout fixed." })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "baseline-summary-card", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "One modeling question" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "Does routing prediction through explicit thermodynamics help beyond the same backbone trained directly?" })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "baseline-summary-card", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "Descriptor path stays fair" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "DirectGNN+descriptors augments the pair representation rather than changing the upstream graph stack." })
            ] })
          ] })
        ] })
      }
    );
  }
  function Figure3BDiagnostics() {
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
      FigureCard,
      {
        kicker: "Figure 3B",
        title: "Solver-Facing Diagnostics",
        subtitle: "`model.forward(...)` exposes both raw head outputs and the values that actually enter the solver, which makes oracle/GC diagnostics auditable.",
        footer: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
          FigureLegend,
          {
            items: [
              { label: "raw predictions", color: "rgba(37, 99, 235, 0.70)" },
              { label: "solver-facing substitution", color: "rgba(245, 158, 11, 0.70)" },
              { label: "diagnostic exports", color: "rgba(16, 185, 129, 0.70)" }
            ]
          }
        ),
        children: /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "solver-diag-slide", children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "solver-diag-header", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(ExamplePairStrip, { compact: true }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "solver-diag-formula-card", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "pipeline-builder__eyebrow", children: "solver substitution" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexBlock, { children: "\\theta_{solver} = (1-m)\\odot\\theta_{pred} + m\\odot\\theta_{oracle}" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("p", { className: "figure-subnote", children: [
                "During normal inference ",
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "m=0" }),
                ". In oracle diagnostics, supervised",
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "T_m" }),
                " and ",
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "\\Delta H_{fus}" }),
                " can replace only the solver-facing branch while the raw head outputs remain intact for losses and analysis."
              ] })
            ] })
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "solver-diag-grid", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("section", { className: "solver-diag-column", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "solver-diag-column__title", children: "1. Raw network outputs" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "solver-diag-card", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("code", { children: "fusion_params" }) }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "T_m,\\ \\Delta H_{fus},\\ \\Delta C_p" }),
                  " directly from ",
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("code", { children: "FusionHead" }),
                  "."
                ] })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "solver-diag-card", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("code", { children: "nrtl_params" }) }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "\\tau_{12}(T),\\ \\tau_{21}(T),\\ \\alpha" }),
                  " from the pair embedding plus temperature."
                ] })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "solver-diag-card", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "auxiliary outputs" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("code", { children: "hansen_sol" }),
                  ", ",
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("code", { children: "hansen_slv" }),
                  ", ",
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("code", { children: "aux_sol" }),
                  ", ",
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("code", { children: "aux_slv" }),
                  ", ",
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("code", { children: "Ra" }),
                  "."
                ] })
              ] })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("section", { className: "solver-diag-column", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "solver-diag-column__title", children: "2. Values sent into the solver" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "solver-diag-card solver-diag-card--accent", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("code", { children: "fusion_gc_priors" }) }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { children: [
                  "When crystal GC priors are enabled, the residual branch starts from calibrated ",
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "T_m^{GC}" }),
                  "."
                ] })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "solver-diag-arrow", children: "\u2193" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "solver-diag-card solver-diag-card--accent", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("code", { children: "solver_fusion_params" }) }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { children: [
                  "Actual crystal parameters entering ",
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("code", { children: "SLESolver" }),
                  " after GC/oracle substitution."
                ] })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "solver-diag-arrow", children: "\u2193" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "solver-diag-card solver-diag-card--accent", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("code", { children: "corrected_fusion_params" }) }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "Bounded parameter deltas rerun the solver without bypassing physics." })
              ] })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("section", { className: "solver-diag-column", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "solver-diag-column__title", children: "3. Exported intermediates" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "solver-diag-card", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("code", { children: "oracle_injection_masks" }) }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "Records which samples actually received train-time oracle substitution." })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "solver-diag-card", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("code", { children: "return_intermediates=True" }) }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "\\Phi,\\ \\ln\\gamma_2,\\ \\ln x_{2,physics},\\ \\ln x_{2,final}" }),
                  " and solver-facing tensors become flat exports."
                ] })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "solver-diag-card", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "experiment surface" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("code", { children: "run_full_budget_experiment.py" }),
                  " writes diagnostics such as ",
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("code", { children: "tgnn_intermediates.csv" }),
                  " for downstream analysis."
                ] })
              ] })
            ] })
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "solver-diag-summary", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "solver-diag-summary__item", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "raw path" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("code", { children: "fusion_params" }),
                " stay available for supervised auxiliary losses."
              ] })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "solver-diag-summary__item", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "solver path" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("code", { children: "solver_fusion_params" }),
                " make train-time substitution explicit instead of implicit."
              ] })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "solver-diag-summary__item", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "analysis path" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "Intermediates expose whether the bottleneck sits in representation, crystal terms, interaction terms, or correction." })
            ] })
          ] })
        ] })
      }
    );
  }
  function Figure4Solver() {
    const xMin = 1e-3;
    const xMax = 0.08;
    const yMin = -4.8;
    const yMax = 0.4;
    const iterations = [0.05, 5216e-6, 3424e-6, 335296e-8, 335012e-8];
    const [visibleSteps, setVisibleSteps] = (0, import_react3.useState)(4);
    const width = 520;
    const height = 300;
    const left = 58;
    const top = 24;
    const plotWidth = 420;
    const plotHeight = 210;
    const xScale = (value) => left + (value - xMin) / (xMax - xMin) * plotWidth;
    const yScale = (value) => top + plotHeight - (value - yMin) / (yMax - yMin) * plotHeight;
    const demand = (x) => Math.log(Math.max(x, 8e-4)) + 2.35;
    const supply = (x) => -3.35 + 3.45 * ((1 - Math.exp(-15 * x)) / (1 - Math.exp(-4.5)));
    const curveXs = Array.from({ length: 180 }, (_, index) => xMin + (xMax - xMin) * index / 179);
    const demandPath = linePath(curveXs.map((value) => [xScale(value), yScale(demand(value))]));
    const supplyPath = linePath(curveXs.map((value) => [xScale(value), yScale(supply(value))]));
    const cobwebSegments = [];
    for (let index = 0; index < visibleSteps; index += 1) {
      const current = iterations[index];
      const next = iterations[index + 1];
      if (next === void 0) {
        continue;
      }
      const yDemand = demand(current);
      cobwebSegments.push([
        [xScale(current), yScale(yMin)],
        [xScale(current), yScale(yDemand)],
        [xScale(next), yScale(yDemand)],
        [xScale(next), yScale(yMin)]
      ]);
    }
    const convergenceWidth = 360;
    const convergenceHeight = 240;
    const convLeft = 44;
    const convTop = 28;
    const convXScale = (value) => convLeft + value / 10 * 280;
    const convYScale = (value) => convTop + 170 - (value - 0) / 0.055 * 170;
    const convPoints = iterations.map((value, index) => [convXScale(index), convYScale(value)]);
    const activeStepFrom = iterations[Math.max(0, visibleSteps - 1)];
    const activeStepTo = iterations[visibleSteps];
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
      FigureCard,
      {
        kicker: "Figure 4",
        title: "SLE Solver",
        subtitle: "Successive substitution contracts quickly to the equilibrium solubility root.",
        controls: /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("label", { className: "slider-control", children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { children: [
            "Show iterations: ",
            visibleSteps
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
            "input",
            {
              type: "range",
              min: "1",
              max: "4",
              value: visibleSteps,
              onChange: (event) => setVisibleSteps(Number(event.target.value))
            }
          )
        ] }),
        footer: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
          StatStrip,
          {
            items: [
              { label: "x\u2082\u2070", value: "0.050" },
              { label: "x\u2082*", value: "0.00335" },
              { label: "|g'|", value: "\u22480.04" }
            ]
          }
        ),
        children: /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "solver-grid", children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "solver-panel", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "solver-panel__title", children: "A. Graphical intersection (zoomed to the active region)" }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("svg", { viewBox: `0 0 ${width} ${height}`, role: "img", "aria-label": "Graphical SLE intersection", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("defs", { children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("clipPath", { id: "solver-clip-a", children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("rect", { x: left, y: top, width: plotWidth, height: plotHeight, rx: "18" }) }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("marker", { id: "solver-step-arrow", viewBox: "0 0 10 10", refX: "8", refY: "5", markerWidth: "7", markerHeight: "7", orient: "auto", children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("path", { d: "M 0 0 L 10 5 L 0 10 z", fill: COLORS.orange }) })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("rect", { x: left, y: top, width: plotWidth, height: plotHeight, fill: PAPER_FILL, rx: "18" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("line", { x1: left, y1: top + plotHeight, x2: left + plotWidth, y2: top + plotHeight, stroke: COLORS.line, strokeWidth: "2" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("line", { x1: left, y1: top, x2: left, y2: top + plotHeight, stroke: COLORS.line, strokeWidth: "2" }),
              [2e-3, 0.01, 0.02, 0.04, 0.06, 0.08].map((tick) => /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("g", { children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                  "line",
                  {
                    x1: xScale(tick),
                    y1: top + plotHeight,
                    x2: xScale(tick),
                    y2: top + plotHeight + 6,
                    stroke: COLORS.line
                  }
                ),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("text", { x: xScale(tick), y: top + plotHeight + 22, textAnchor: "middle", fontSize: "13", fill: PAPER_SOFT_TEXT, children: tick < 0.01 ? tick.toFixed(3) : tick.toFixed(2) })
              ] }, tick)),
              [-4, -3, -2, -1, 0].map((tick) => /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("g", { children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("line", { x1: left - 6, y1: yScale(tick), x2: left, y2: yScale(tick), stroke: COLORS.line }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("text", { x: left - 12, y: yScale(tick) + 4, textAnchor: "end", fontSize: "13", fill: PAPER_SOFT_TEXT, children: tick })
              ] }, tick)),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("g", { clipPath: "url(#solver-clip-a)", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("path", { d: demandPath, fill: "none", stroke: COLORS.blue, strokeWidth: "4" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("path", { d: supplyPath, fill: "none", stroke: COLORS.red, strokeWidth: "4" }),
                cobwebSegments.map((segment, index) => /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                  "path",
                  {
                    d: linePath(segment),
                    fill: "none",
                    stroke: COLORS.orange,
                    strokeWidth: index === visibleSteps - 1 ? 3.1 : 2.1,
                    strokeDasharray: "8 7",
                    strokeOpacity: index === visibleSteps - 1 ? 1 : 0.28,
                    markerEnd: index === visibleSteps - 1 ? "url(#solver-step-arrow)" : void 0
                  },
                  `segment-${index}`
                ))
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("circle", { cx: xScale(335e-5), cy: yScale(demand(335e-5)), r: "7", fill: COLORS.green }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("text", { x: left + plotWidth / 2, y: height - 10, textAnchor: "middle", fontSize: "14", fill: PAPER_SOFT_TEXT, children: "x\u2082" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                "text",
                {
                  x: "16",
                  y: top + plotHeight / 2,
                  transform: `rotate(-90 16 ${top + plotHeight / 2})`,
                  fontSize: "14",
                  fill: PAPER_SOFT_TEXT,
                  textAnchor: "middle",
                  children: "y"
                }
              )
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "solver-panel__notes", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "solver-note-line", style: { "--line-color": COLORS.blue } }),
                "Crystal demand: ",
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "\\ln x_2 + \\Phi" })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "solver-note-line", style: { "--line-color": COLORS.red } }),
                "Solvent supply: ",
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "-\\ln\\gamma_2" })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "solver-note-line", style: { "--line-color": COLORS.orange } }),
                "Current step: ",
                activeStepFrom.toFixed(5),
                " \u2192 ",
                activeStepTo.toFixed(5)
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "solver-note-dot" }),
                "Intersection: ",
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "x_2^*" })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
                "View is intentionally zoomed to ",
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "10^{-3} \\le x_2 \\le 8\\cdot10^{-2}" }),
                ", where all practical solver motion happens."
              ] })
            ] })
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "solver-panel", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "solver-panel__title", children: "B. Convergence trace" }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("svg", { viewBox: `0 0 ${convergenceWidth} ${convergenceHeight}`, role: "img", "aria-label": "SLE solver convergence", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("rect", { x: convLeft, y: convTop, width: "280", height: "170", fill: PAPER_FILL, rx: "18" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("line", { x1: convLeft, y1: convTop + 170, x2: convLeft + 280, y2: convTop + 170, stroke: COLORS.line, strokeWidth: "2" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("line", { x1: convLeft, y1: convTop, x2: convLeft, y2: convTop + 170, stroke: COLORS.line, strokeWidth: "2" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                "line",
                {
                  x1: convLeft,
                  y1: convYScale(335e-5),
                  x2: convLeft + 280,
                  y2: convYScale(335e-5),
                  stroke: COLORS.green,
                  strokeWidth: "2",
                  strokeDasharray: "6 6"
                }
              ),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("path", { d: linePath(convPoints), fill: "none", stroke: COLORS.blue, strokeWidth: "4" }),
              convPoints.map(([x, y], index) => /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                "circle",
                {
                  cx: x,
                  cy: y,
                  r: index <= visibleSteps ? 5 : 3.5,
                  fill: index <= visibleSteps ? COLORS.orange : COLORS.line
                },
                `conv-${index}`
              )),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("text", { x: convLeft + 140, y: convergenceHeight - 16, textAnchor: "middle", fontSize: "14", fill: PAPER_SOFT_TEXT, children: "iteration k" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                "text",
                {
                  x: "16",
                  y: convTop + 85,
                  transform: `rotate(-90 16 ${convTop + 85})`,
                  fontSize: "14",
                  fill: PAPER_SOFT_TEXT,
                  textAnchor: "middle",
                  children: "x\u2082\u207D\u1D4F\u207E"
                }
              )
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "solver-panel__notes", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "x\u2082\u2070" }),
                " = 0.050"
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "x\u2082*" }),
                " = 0.00335"
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { children: "Convergence in 4 iterations" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "|g'| \\approx 0.04" }),
                " so the map is a strong contraction."
              ] })
            ] })
          ] })
        ] })
      }
    );
  }
  function Figure5Backprop() {
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)(
      FigureCard,
      {
        kicker: "Figure 5",
        title: "Implicit Differentiation vs Unrolled Backprop",
        subtitle: "Backward through the fixed point avoids O(N) memory and unstable chain products.",
        children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "compare-grid compare-grid--rebuilt", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("section", { className: "compare-lane compare-lane--warn", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "compare-lane__title", children: "A. Unrolled solver graph" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "compare-stack", children: ["\\theta", "x_2^{(0)}", "\\mathrm{NRTL}", "x_2^{(1)}", "\\mathrm{NRTL}", "x_2^{(2)}", "\\cdots", "x_2^{(N)}", "\\mathcal{L}"].map((item, index) => /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)(import_react3.default.Fragment, { children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "compare-node", children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: item }) }),
                index < 8 ? /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "compare-arrow compare-arrow--warn", children: "\u2193" }) : null
              ] }, `${item}-${index}`)) }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "compare-backward-box compare-backward-box--warn", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "Backward path" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexBlock, { children: "\\prod_k g'(x_2^{(k)})" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("p", { className: "figure-subnote", children: "Stores every iterate and risks vanishing or exploding sensitivity." })
              ] })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("section", { className: "compare-lane compare-lane--success", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "compare-lane__title", children: "B. Implicit fixed-point backward" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "compare-implicit-card", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "compare-node", children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "\\theta" }) }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "compare-arrow compare-arrow--success", children: "\u2192" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "compare-node compare-node--wide", children: [
                  "Forward: iterate to ",
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "x_2^*" })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "compare-arrow compare-arrow--success", children: "\u2192" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "compare-node", children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "\\mathcal{L}" }) })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "compare-backward-box", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "Single backward step" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexBlock, { children: "\\frac{d x_2^*}{d\\theta} = -\\frac{\\partial F/\\partial \\theta}{\\partial F/\\partial x_2^*}" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("p", { className: "figure-subnote", children: "Exact at the converged fixed point and O(1) in memory." })
              ] })
            ] })
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("table", { className: "comparison-table comparison-table--tight", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("thead", { children: /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("tr", { children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("th", { children: "Method" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("th", { children: "Memory" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("th", { children: "Accuracy" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("th", { children: "Stability" })
            ] }) }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("tbody", { children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("tr", { children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("td", { children: "Unrolled" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("td", { children: "O(N\xB7B)" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("td", { children: "~(1-|g'|\u1D3A)" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("td", { children: "|g'|\u1D3A risk" })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("tr", { children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("td", { children: "Implicit" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("td", { children: "O(B)" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("td", { children: "~100%" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("td", { children: "Stable + clamp" })
              ] })
            ] })
          ] })
        ]
      }
    );
  }
  function buildStackedAreas(rows, seriesKeys) {
    const width = 420;
    const height = 240;
    const left = 50;
    const top = 18;
    const plotWidth = 320;
    const plotHeight = 170;
    const xScale = (epoch) => left + epoch / 10 * plotWidth;
    const yScale = (value) => top + plotHeight - value / 100 * plotHeight;
    let baseline = rows.map(() => 0);
    const layers = seriesKeys.map((key) => {
      const topPoints = rows.map((row, index) => [xScale(row.epoch), yScale(baseline[index] + row[key])]);
      const bottomPoints = rows.map((row, index) => [xScale(row.epoch), yScale(baseline[index])]);
      baseline = baseline.map((value, index) => value + rows[index][key]);
      return { key, path: areaPath(topPoints, bottomPoints) };
    });
    return { layers, width, height, left, top, plotWidth, plotHeight, xScale, yScale };
  }
  function StackedAreaChart({ title, rows, colors, activeKey, annotation }) {
    const keys = Object.keys(colors);
    const chart = buildStackedAreas(rows, keys);
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "loss-chart", children: [
      /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "loss-chart__title", children: title }),
      /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("svg", { viewBox: `0 0 ${chart.width} ${chart.height}`, role: "img", "aria-label": title, children: [
        /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("rect", { x: chart.left, y: chart.top, width: chart.plotWidth, height: chart.plotHeight, fill: PAPER_FILL, rx: "18" }),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
          "line",
          {
            x1: chart.left,
            y1: chart.top + chart.plotHeight,
            x2: chart.left + chart.plotWidth,
            y2: chart.top + chart.plotHeight,
            stroke: COLORS.line,
            strokeWidth: "2"
          }
        ),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("line", { x1: chart.left, y1: chart.top, x2: chart.left, y2: chart.top + chart.plotHeight, stroke: COLORS.line, strokeWidth: "2" }),
        [0, 50, 100].map((tick) => /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("g", { children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("line", { x1: chart.left - 6, y1: chart.yScale(tick), x2: chart.left, y2: chart.yScale(tick), stroke: COLORS.line }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("text", { x: chart.left - 12, y: chart.yScale(tick) + 4, textAnchor: "end", fontSize: "12", fill: PAPER_SOFT_TEXT, children: [
            tick,
            "%"
          ] })
        ] }, tick)),
        chart.layers.map((layer) => /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
          "path",
          {
            d: layer.path,
            fill: colors[layer.key],
            opacity: activeKey === layer.key || activeKey === "all" ? 0.88 : 0.22
          },
          layer.key
        )),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("text", { x: chart.left + chart.plotWidth / 2, y: chart.height - 10, textAnchor: "middle", fontSize: "13", fill: PAPER_SOFT_TEXT, children: "Phase 2 epoch" }),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
          "text",
          {
            x: "18",
            y: chart.top + chart.plotHeight / 2,
            transform: `rotate(-90 18 ${chart.top + chart.plotHeight / 2})`,
            fontSize: "13",
            fill: PAPER_SOFT_TEXT,
            textAnchor: "middle",
            children: "share of total loss"
          }
        )
      ] }),
      /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("p", { className: "figure-subnote", children: annotation })
    ] });
  }
  function Figure6LossLandscape() {
    const [activeKey, setActiveKey] = (0, import_react3.useState)("sol");
    const beforeRows = [
      { epoch: 0, sol: 35, vant: 40, tm: 10, dh: 7, bridge: 5, tau: 3 },
      { epoch: 2, sol: 18, vant: 63, tm: 7, dh: 5, bridge: 4, tau: 3 },
      { epoch: 4, sol: 9, vant: 80, tm: 5, dh: 3, bridge: 2, tau: 1 },
      { epoch: 6, sol: 4, vant: 91, tm: 2, dh: 1.5, bridge: 1, tau: 0.5 },
      { epoch: 8, sol: 1.5, vant: 97, tm: 0.7, dh: 0.4, bridge: 0.3, tau: 0.1 },
      { epoch: 10, sol: 0.8, vant: 99, tm: 0.1, dh: 0.05, bridge: 0.03, tau: 0.02 }
    ];
    const afterRows = [
      { epoch: 0, sol: 72, vant: 6, tm: 9, dh: 6, bridge: 4, tau: 3 },
      { epoch: 2, sol: 84, vant: 2.5, tm: 5, dh: 4, bridge: 2.5, tau: 2 },
      { epoch: 4, sol: 88, vant: 1.2, tm: 4, dh: 3, bridge: 2.5, tau: 1.3 },
      { epoch: 6, sol: 91, vant: 0.8, tm: 3, dh: 2.5, bridge: 1.7, tau: 1 },
      { epoch: 8, sol: 92, vant: 0.5, tm: 3, dh: 2, bridge: 1.6, tau: 0.9 },
      { epoch: 10, sol: 93, vant: 0.3, tm: 2.7, dh: 1.8, bridge: 1.4, tau: 0.8 }
    ];
    const lossColors = {
      sol: COLORS.blue,
      vant: COLORS.red,
      tm: COLORS.purple,
      dh: COLORS.orange,
      bridge: COLORS.green,
      tau: COLORS.yellow
    };
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
      FigureCard,
      {
        kicker: "Figure 6",
        title: "Loss Landscape",
        subtitle: "Balancing 12 losses only works if solubility keeps the dominant fraction in Phase 2.",
        controls: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
          ToggleGroup,
          {
            label: "Loss highlight",
            options: [
              { label: "sol", value: "sol" },
              { label: "vant_hoff", value: "vant" },
              { label: "all", value: "all" }
            ],
            value: activeKey,
            onChange: setActiveKey
          }
        ),
        footer: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
          FigureLegend,
          {
            items: [
              { label: "sol", color: COLORS.blue },
              { label: "vant_hoff_local", color: COLORS.red },
              { label: "T_m", color: COLORS.purple },
              { label: "dH_fus", color: COLORS.orange },
              { label: "bridge", color: COLORS.green },
              { label: "tau_reg", color: COLORS.yellow }
            ]
          }
        ),
        children: /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "loss-grid", children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
            StackedAreaChart,
            {
              title: "A. Before fix",
              rows: beforeRows,
              colors: lossColors,
              activeKey,
              annotation: "sol_fraction < 1% \u2014 optimizer ignores solubility"
            }
          ),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
            StackedAreaChart,
            {
              title: "B. After fix",
              rows: afterRows,
              colors: lossColors,
              activeKey,
              annotation: "sol_fraction > 85% \u2014 optimizer focuses on solubility"
            }
          )
        ] })
      }
    );
  }
  function Figure7LinearProbe() {
    const { linear_probe: probeData } = usePresentationData();
    const descriptorNotes = {
      FractionCSP3: "Strongly encoded shape and saturation cue.",
      NumHDonors: "Hydrogen-bond donation is partially preserved.",
      TPSA: "Polarity survives, but not cleanly enough for descriptor parity.",
      NumHAcceptors: "Acceptors are learned better than mass-like scalars.",
      MolLogP: "Lipophilicity remains recoverable but not saturated.",
      NumRotatableBonds: "Flexibility is present, though blurred.",
      RingCount: "Ring topology is partially linearly accessible.",
      MolWt: "Mass statistics are unexpectedly lossy for the encoder.",
      HeavyAtomCount: "A simple count should be easy, but the bottleneck discards detail.",
      MolMR: "Polarizability-related structure is among the weaker recovered channels."
    };
    const descriptors = (probeData.descriptors ?? []).map((descriptor) => ({
      ...descriptor,
      note: descriptorNotes[descriptor.name] ?? "Recovered automatically from the latest descriptor-probe artifact."
    }));
    const [selectedIndex, setSelectedIndex] = (0, import_react3.useState)(0);
    const selectedDescriptor = descriptors[Math.min(selectedIndex, Math.max(0, descriptors.length - 1))] ?? descriptors[0];
    const donutCircumference = 2 * Math.PI * 54;
    const donutSegments = [
      {
        label: "R\xB2 \u2265 0.8",
        fraction: (probeData.counts?.ge_0_8 ?? 3) / (probeData.total_descriptors ?? 208),
        color: COLORS.green
      },
      {
        label: "0.5\u20130.8",
        fraction: (probeData.counts?.between_0_5_and_0_8 ?? 104) / (probeData.total_descriptors ?? 208),
        color: COLORS.yellow
      },
      {
        label: "R\xB2 < 0.5",
        fraction: (probeData.counts?.lt_0_5 ?? 101) / (probeData.total_descriptors ?? 208),
        color: COLORS.red
      }
    ];
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
      FigureCard,
      {
        kicker: "Figure 7",
        title: "Linear Probe",
        subtitle: "The encoder only retains about half of the descriptor information that a direct descriptor model sees.",
        footer: /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "figure-footer-note", children: [
          "RF sees all descriptors at ",
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "R\xB2 = 1.0" }),
          ", leaving a measured encoder gap of ",
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "0.68 MAE" }),
          "."
        ] }),
        children: /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "probe-grid", children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "probe-bars", role: "img", "aria-label": "Descriptor recovery bar chart", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "probe-bars__median", children: [
              "median R\xB2 = ",
              probeData.median_r2_label ?? "0.505"
            ] }),
            descriptors.map((descriptor, index) => {
              const barColor = descriptor.value >= 0.8 ? COLORS.green : descriptor.value >= 0.5 ? COLORS.yellow : COLORS.red;
              return /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)(
                "button",
                {
                  type: "button",
                  className: `probe-row${selectedIndex === index ? " is-active" : ""}`,
                  onClick: () => setSelectedIndex(index),
                  children: [
                    /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "probe-row__label", children: descriptor.name }),
                    /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { className: "probe-row__track", children: [
                      /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "probe-row__fill", style: { width: `${descriptor.value * 100}%`, background: barColor } }),
                      /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "probe-row__midline" })
                    ] }),
                    /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "probe-row__value", children: descriptor.value.toFixed(2) })
                  ]
                },
                descriptor.name
              );
            })
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "probe-sidepanel", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "probe-detail", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "probe-detail__eyebrow", children: "Selected descriptor" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("h3", { children: selectedDescriptor?.name ?? "Descriptor" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("p", { children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("strong", { children: [
                  "R\xB2 = ",
                  selectedDescriptor?.value?.toFixed(2) ?? "\u2014"
                ] }),
                ". ",
                selectedDescriptor?.note ?? ""
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("p", { className: "figure-subnote", children: "Green means well learned, yellow means partial retention, and red signals a real encoder bottleneck." })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "probe-donut", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("svg", { viewBox: "0 0 180 180", role: "img", "aria-label": "Descriptor recovery donut", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("circle", { cx: "90", cy: "90", r: "54", fill: "none", stroke: PAPER_BORDER, strokeWidth: "22" }),
                donutSegments.map((segment, index) => {
                  const previousFraction = donutSegments.slice(0, index).reduce((sum, item) => sum + item.fraction, 0);
                  return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                    "circle",
                    {
                      cx: "90",
                      cy: "90",
                      r: "54",
                      fill: "none",
                      stroke: segment.color,
                      strokeWidth: "22",
                      strokeDasharray: `${segment.fraction * donutCircumference} ${donutCircumference}`,
                      strokeDashoffset: -previousFraction * donutCircumference,
                      transform: "rotate(-90 90 90)"
                    },
                    segment.label
                  );
                }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("text", { x: "90", y: "82", textAnchor: "middle", fontSize: "24", fontWeight: "800", fill: PAPER_TEXT, children: [
                  Math.round((probeData.counts?.between_0_5_and_0_8 ?? 104) / (probeData.total_descriptors ?? 208) * 100),
                  "%"
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("text", { x: "90", y: "104", textAnchor: "middle", fontSize: "10", fill: PAPER_SOFT_TEXT, children: "captured" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("text", { x: "90", y: "118", textAnchor: "middle", fontSize: "10", fill: PAPER_SOFT_TEXT, children: "descriptor info" })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "probe-donut__legend", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
                  probeData.counts?.ge_0_8 ?? 3,
                  " / ",
                  probeData.total_descriptors ?? 208,
                  " well learned"
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
                  probeData.counts?.between_0_5_and_0_8 ?? 104,
                  " / ",
                  probeData.total_descriptors ?? 208,
                  " partial"
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
                  probeData.counts?.lt_0_5 ?? 101,
                  " / ",
                  probeData.total_descriptors ?? 208,
                  " poor"
                ] })
              ] })
            ] })
          ] })
        ] })
      }
    );
  }
  function Figure8Waterfall() {
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
      FigureCard,
      {
        kicker: "Figure 8",
        title: "Error Decomposition",
        subtitle: "Most of the gap to the best descriptor model is upstream of the physics bottleneck.",
        children: /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "waterfall-grid", children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "waterfall-card", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "waterfall-card__title", children: "Current path" }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "waterfall-steps", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "waterfall-step waterfall-step--base", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "RF (descriptors)" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "1.20 MAE" })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "waterfall-step waterfall-step--delta", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "+ GNN encoder gap" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "+0.68" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("small", { children: "93% of total gap" })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "waterfall-step waterfall-step--minor", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "+ Physics bottleneck" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "+0.05" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("small", { children: "7% of total gap" })
              ] })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "waterfall-totals", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "1.88" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "DirectGNN" })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "1.93" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "TGNN (current)" })
              ] })
            ] })
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "waterfall-card waterfall-card--expected", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "waterfall-card__title", children: "Expected with descriptor augmentation" }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "waterfall-steps waterfall-steps--expected", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "waterfall-step waterfall-step--base", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "RF (descriptors)" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "1.20 MAE" })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "waterfall-step waterfall-step--target", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "TGNN + descriptors" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "1.15\u20131.35" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("small", { children: "Physics can help after the encoder gap closes." })
              ] })
            ] })
          ] })
        ] })
      }
    );
  }
  function chartPathFromTemps(temps, fn, xScale, yScale) {
    return linePath(temps.map((temp) => [xScale(temp), yScale(fn(temp))]));
  }
  function Figure9TemperatureExtrapolation() {
    const trainTemps = [280, 300, 320, 340];
    const testTemps = [350, 360, 380];
    const allTemps = Array.from({ length: 90 }, (_, index) => 250 + 150 * index / 89);
    const trueCurve = (temp) => -2600 / temp + 5.2;
    const rfCurve = (temp) => {
      if (temp <= 340) {
        return trueCurve(temp) + 0.08 * Math.sin((temp - 280) / 22);
      }
      return trueCurve(340) - 0.02;
    };
    const tgnnCurve = (temp) => trueCurve(temp) + 0.03 * Math.sin((temp - 260) / 50);
    const width = 420;
    const height = 270;
    const left = 52;
    const top = 20;
    const plotWidth = 320;
    const plotHeight = 190;
    const xScale = (temp) => left + (temp - 250) / 150 * plotWidth;
    const yScale = (value) => top + plotHeight - (value + 10) / 10 * plotHeight;
    function Panel({ title, subtitle, prediction, color }) {
      return /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "temperature-panel", children: [
        /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "temperature-panel__title", children: title }),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("p", { className: "figure-subnote", children: subtitle }),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("svg", { viewBox: `0 0 ${width} ${height}`, role: "img", "aria-label": title, children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("rect", { x: left, y: top, width: plotWidth, height: plotHeight, fill: PAPER_FILL, rx: "18" }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("rect", { x: xScale(280), y: top, width: xScale(340) - xScale(280), height: plotHeight, fill: "rgba(148, 163, 184, 0.10)" }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("line", { x1: left, y1: top + plotHeight, x2: left + plotWidth, y2: top + plotHeight, stroke: COLORS.line, strokeWidth: "2" }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("line", { x1: left, y1: top, x2: left, y2: top + plotHeight, stroke: COLORS.line, strokeWidth: "2" }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("path", { d: chartPathFromTemps(allTemps, trueCurve, xScale, yScale), fill: "none", stroke: PAPER_TEXT, strokeDasharray: "7 7", strokeWidth: "2.5" }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("path", { d: chartPathFromTemps(allTemps, prediction, xScale, yScale), fill: "none", stroke: color, strokeWidth: "4" }),
          trainTemps.map((temp) => /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("circle", { cx: xScale(temp), cy: yScale(trueCurve(temp)), r: "5.2", fill: COLORS.blue }, `train-${temp}`)),
          testTemps.map((temp) => /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("circle", { cx: xScale(temp), cy: yScale(trueCurve(temp)), r: "5.2", fill: COLORS.red }, `test-${temp}`)),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("text", { x: left + 8, y: top + 18, fill: COLORS.gray, fontSize: "12", children: "train range" }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("text", { x: left + plotWidth / 2, y: height - 10, textAnchor: "middle", fontSize: "14", fill: PAPER_SOFT_TEXT, children: "Temperature T (K)" }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
            "text",
            {
              x: "16",
              y: top + plotHeight / 2,
              transform: `rotate(-90 16 ${top + plotHeight / 2})`,
              fontSize: "14",
              fill: PAPER_SOFT_TEXT,
              textAnchor: "middle",
              children: "ln x\u2082"
            }
          )
        ] })
      ] });
    }
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
      FigureCard,
      {
        kicker: "Figure 9",
        title: "Temperature Extrapolation",
        subtitle: "Schematic: tree models flatten outside seen temperatures; the physics-guided path preserves a van't Hoff-like trend.",
        footer: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "figure-footer-note", children: "Schematic. Quantitative results pending." }),
        children: /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "temperature-grid", children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(Panel, { title: "A. RF: no temperature physics", subtitle: "Flat extrapolation beyond 340 K", prediction: rfCurve, color: COLORS.gray }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
            Panel,
            {
              title: "B. TGNN: SLE-guided extrapolation",
              subtitle: "d(ln x\u2082)/dT = \u0394H_sol / (RT\xB2) is baked into the solver",
              prediction: tgnnCurve,
              color: COLORS.blue
            }
          )
        ] })
      }
    );
  }
  var curriculumRows = [
    {
      label: "GNN Encoder",
      segments: [{ from: 0, to: 300, type: "train", text: "train" }]
    },
    {
      label: "Crystal Heads",
      segments: [
        { from: 0, to: 50, type: "train", text: "train" },
        { from: 50, to: 250, type: "low", text: "low lr" },
        { from: 250, to: 300, type: "train", text: "unfreeze" }
      ]
    },
    {
      label: "NRTL Head",
      segments: [
        { from: 0, to: 50, type: "off", text: "off" },
        { from: 50, to: 300, type: "train", text: "train" }
      ]
    },
    {
      label: "SLE Solver",
      segments: [
        { from: 0, to: 50, type: "off", text: "off" },
        { from: 50, to: 300, type: "train", text: "active" }
      ]
    },
    {
      label: "Correction",
      segments: [
        { from: 0, to: 70, type: "off", text: "off" },
        { from: 70, to: 300, type: "train", text: "train" }
      ]
    },
    {
      label: "L_sol",
      segments: [
        { from: 0, to: 50, type: "off", text: "0" },
        { from: 50, to: 300, type: "train", text: "dominant" }
      ]
    },
    {
      label: "L_aux (T_m, \u0394H)",
      segments: [
        { from: 0, to: 50, type: "train", text: "dominant" },
        { from: 50, to: 300, type: "low", text: "light" }
      ]
    },
    {
      label: "Oracle Injection",
      segments: [
        { from: 0, to: 50, type: "off", text: "off" },
        { from: 50, to: 200, type: "train", text: "active" },
        { from: 200, to: 250, type: "low", text: "anneal" },
        { from: 250, to: 300, type: "off", text: "off" }
      ]
    }
  ];
  function statusAtEpoch(segments, epoch) {
    return segments.find((segment) => epoch >= segment.from && epoch < segment.to) ?? segments[segments.length - 1];
  }
  function Figure10Curriculum() {
    const [epoch, setEpoch] = (0, import_react3.useState)(92);
    const phaseLabel = epoch < 50 ? "Phase 1" : epoch < 250 ? "Phase 2" : "Phase 3";
    const milestones = [
      { epoch: 50, label: "SLE activated, L_sol starts" },
      { epoch: 70, label: "Correction unfreezes" },
      { epoch: 200, label: "Oracle annealing" }
    ];
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
      FigureCard,
      {
        kicker: "Figure 10",
        title: "Three-Phase Curriculum",
        subtitle: "The training schedule gates physics and correction capacity in stages instead of turning everything on at once.",
        controls: /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("label", { className: "slider-control", children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { children: [
            "Epoch marker: ",
            epoch
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("input", { type: "range", min: "0", max: "299", value: epoch, onChange: (event) => setEpoch(Number(event.target.value)) })
        ] }),
        footer: /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "figure-footer-note", children: [
          "Current marker is in ",
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: phaseLabel }),
          "."
        ] }),
        children: /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "curriculum-grid", children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "curriculum-chart", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "curriculum-phases", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "curriculum-phase curriculum-phase--one", children: "Phase 1 \xB7 50 epochs" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "curriculum-phase curriculum-phase--two", children: "Phase 2 \xB7 200 epochs" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "curriculum-phase curriculum-phase--three", children: "Phase 3 \xB7 50 epochs" })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "curriculum-rows", children: curriculumRows.map((row) => /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "curriculum-row", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "curriculum-row__label", children: row.label }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "curriculum-track", children: [
                row.segments.map((segment) => /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                  "div",
                  {
                    className: `curriculum-segment curriculum-segment--${segment.type}`,
                    style: {
                      left: `${segment.from / 300 * 100}%`,
                      width: `${(segment.to - segment.from) / 300 * 100}%`
                    },
                    children: segment.text
                  },
                  `${row.label}-${segment.from}`
                )),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "curriculum-marker", style: { left: `${epoch / 300 * 100}%` } })
              ] })
            ] }, row.label)) })
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "curriculum-panel", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("h3", { children: [
              "State at epoch ",
              epoch
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("ul", { className: "curriculum-status-list", children: curriculumRows.map((row) => {
              const state = statusAtEpoch(row.segments, epoch);
              return /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("li", { children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("strong", { children: [
                  row.label,
                  ":"
                ] }),
                " ",
                state.text
              ] }, `${row.label}-status`);
            }) }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
              FigureLegend,
              {
                items: [
                  { label: "Active training", color: COLORS.green },
                  { label: "Frozen / off", color: COLORS.red },
                  { label: "Low LR / anneal", color: COLORS.yellow }
                ]
              }
            ),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "curriculum-milestone-list", children: milestones.map((milestone) => /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "curriculum-milestone-card", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("strong", { children: [
                "Epoch ",
                milestone.epoch
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: milestone.label })
            ] }, milestone.epoch)) })
          ] })
        ] })
      }
    );
  }
  function Figure11GCPriors() {
    const examples = [
      { key: "paracetamol", name: "Paracetamol", gc: 460, truth: 442, residual: -18 },
      { key: "aspirin", name: "Aspirin", gc: 430, truth: 409, residual: -21 }
    ];
    const [exampleKey, setExampleKey] = (0, import_react3.useState)("paracetamol");
    const example = examples.find((item) => item.key === exampleKey) ?? examples[0];
    const axisPercent = (value) => `${(value - 100) / 600 * 100}%`;
    const truthStart = example.truth - 18;
    const truthEnd = example.truth + 18;
    const priorStart = example.gc - 50;
    const priorEnd = example.gc + 50;
    const randomInit = Math.min(680, example.truth + 165);
    const axisTicks = [100, 250, 400, 550, 700];
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)(
      FigureCard,
      {
        kicker: "Figure 11",
        title: "GC Priors",
        subtitle: "A bounded residual around a group-contribution estimate collapses the crystal-property search space.",
        controls: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
          ToggleGroup,
          {
            label: "Example molecule",
            options: examples.map((item) => ({ label: item.name, value: item.key })),
            value: exampleKey,
            onChange: setExampleKey
          }
        ),
        children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "gc-rebuilt", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "gc-topbar", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "gc-badge-large", children: "6\xD7 smaller search space" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "gc-formula-card", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexBlock, { children: "T_m = T_m^{GC} + \\delta,\\qquad |\\delta| \\le 50\\,K" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("p", { className: "figure-subnote", children: "The model learns a bounded residual around a calibrated group-contribution estimate instead of searching the full crystal-property range." })
              ] })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "gc-range-grid", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "gc-range-card", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "gc-panel__title", children: "A. Without GC prior" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "gc-axis-card", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "gc-axis", children: [
                    /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "gc-axis__track" }),
                    /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "gc-axis__band gc-axis__band--search", style: { left: axisPercent(100), width: "100%" } }),
                    /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                      "div",
                      {
                        className: "gc-axis__band gc-axis__band--truth",
                        style: { left: axisPercent(truthStart), width: `calc(${axisPercent(truthEnd)} - ${axisPercent(truthStart)})` }
                      }
                    ),
                    /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "gc-axis__pin gc-axis__pin--random", style: { left: axisPercent(randomInit) } }),
                    axisTicks.map((tick) => /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "gc-axis__tick", style: { left: axisPercent(tick) }, children: tick }, `without-${tick}`))
                  ] }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "gc-axis__legend", children: [
                    /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
                      /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "gc-swatch gc-swatch--search" }),
                      " search window: 100\u2013700 K"
                    ] }),
                    /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
                      /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "gc-swatch gc-swatch--truth" }),
                      " true melting-point neighborhood"
                    ] }),
                    /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
                      /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "gc-swatch gc-swatch--random" }),
                      " random initialization"
                    ] })
                  ] })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "gc-note-list", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { children: "The fusion head has to search a 600 K interval before it learns anything useful." }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { children: "Sparse crystal supervision means early updates can point in the wrong direction." }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { children: "A poor starting point propagates directly into the SLE solver." })
                ] })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "gc-range-card", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "gc-panel__title", children: "B. With GC prior" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "gc-axis-card", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "gc-axis", children: [
                    /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "gc-axis__track" }),
                    /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                      "div",
                      {
                        className: "gc-axis__band gc-axis__band--prior",
                        style: { left: axisPercent(priorStart), width: `calc(${axisPercent(priorEnd)} - ${axisPercent(priorStart)})` }
                      }
                    ),
                    /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                      "div",
                      {
                        className: "gc-axis__band gc-axis__band--truth",
                        style: { left: axisPercent(truthStart), width: `calc(${axisPercent(truthEnd)} - ${axisPercent(truthStart)})` }
                      }
                    ),
                    /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "gc-axis__pin gc-axis__pin--prior", style: { left: axisPercent(example.gc) } }),
                    /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "gc-axis__pin gc-axis__pin--target", style: { left: axisPercent(example.truth) } }),
                    axisTicks.map((tick) => /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "gc-axis__tick", style: { left: axisPercent(tick) }, children: tick }, `with-${tick}`))
                  ] }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "gc-axis__legend", children: [
                    /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
                      /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "gc-swatch gc-swatch--prior" }),
                      " GC prior window: ",
                      priorStart,
                      "\u2013",
                      priorEnd,
                      " K"
                    ] }),
                    /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
                      /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "gc-swatch gc-swatch--truth" }),
                      " true melting-point neighborhood"
                    ] }),
                    /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
                      /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { className: "gc-swatch gc-swatch--target" }),
                      " bounded residual only needs ",
                      example.residual,
                      " K"
                    ] })
                  ] })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "gc-note-list", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { children: "The model starts near a chemically plausible melting point." }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { children: "Training only has to learn a small correction, not rediscover the whole scale." }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { children: "The solver receives stable crystal parameters much earlier in training." })
                ] })
              ] })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "gc-example-flow", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "gc-example-step", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "Joback prior" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { children: [
                  example.gc,
                  " K"
                ] })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "gc-example-arrow", children: "\u2192" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "gc-example-step", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "Needed residual" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { children: [
                  example.residual,
                  " K"
                ] })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "gc-example-arrow", children: "\u2192" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "gc-example-step", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "True target" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { children: [
                  example.truth,
                  " K"
                ] })
              ] })
            ] })
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "gc-example-card gc-example-card--rebuilt", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: example.name }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { children: [
              "T_m^GC = ",
              example.gc,
              " K"
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { children: [
              "T_m^true = ",
              example.truth,
              " K"
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { children: [
              "Residual needed: ",
              example.residual,
              " K \u2713 (within \xB150 K)"
            ] })
          ] })
        ]
      }
    );
  }
  var overfitEpochs = Array.from({ length: 11 }, (_, index) => index);
  var overfitTrain = [0.75, 0.58, 0.45, 0.35, 0.28, 0.24, 0.23, 0.22, 0.215, 0.212, 0.21];
  var overfitVal = [1.97, 1.95, 1.94, 1.935, 1.93, 1.929, 1.932, 1.94, 1.948, 1.955, 1.96];
  var overfitTau = [0.56, 0.8, 1.1, 1.4, 1.8, 2.1, 2.28, 2.4, 2.52, 2.58, 2.64];
  var overfitSol = [0.926, 0.92, 0.905, 0.89, 0.872, 0.86, 0.848, 0.838, 0.832, 0.827, 0.821];
  function MiniLineChart({
    title,
    values,
    secondaryValues,
    yDomain,
    markerEpoch,
    highlightValue,
    accent,
    secondaryAccent,
    note
  }) {
    const width = 360;
    const height = 180;
    const left = 42;
    const top = 16;
    const plotWidth = 280;
    const plotHeight = 120;
    const xScale = (epoch) => left + epoch / 10 * plotWidth;
    const yScale = (value) => top + plotHeight - (value - yDomain[0]) / (yDomain[1] - yDomain[0]) * plotHeight;
    const path = linePath(overfitEpochs.map((epoch, index) => [xScale(epoch), yScale(values[index])]));
    const secondaryPath = secondaryValues ? linePath(overfitEpochs.map((epoch, index) => [xScale(epoch), yScale(secondaryValues[index])])) : null;
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "mini-chart", children: [
      /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "mini-chart__title", children: title }),
      /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("p", { className: "figure-subnote", children: note }),
      /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("svg", { viewBox: `0 0 ${width} ${height}`, role: "img", "aria-label": title, children: [
        /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("rect", { x: left, y: top, width: plotWidth, height: plotHeight, fill: PAPER_FILL, rx: "18" }),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("rect", { x: xScale(5), y: top, width: xScale(10) - xScale(5), height: plotHeight, fill: "rgba(148, 163, 184, 0.10)" }),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("line", { x1: left, y1: top + plotHeight, x2: left + plotWidth, y2: top + plotHeight, stroke: COLORS.line, strokeWidth: "2" }),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("line", { x1: left, y1: top, x2: left, y2: top + plotHeight, stroke: COLORS.line, strokeWidth: "2" }),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("line", { x1: xScale(5), y1: top, x2: xScale(5), y2: top + plotHeight, stroke: COLORS.green, strokeWidth: "2" }),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
          "line",
          {
            x1: xScale(markerEpoch),
            y1: top,
            x2: xScale(markerEpoch),
            y2: top + plotHeight,
            stroke: COLORS.orange,
            strokeWidth: "2",
            strokeDasharray: "5 5"
          }
        ),
        highlightValue !== void 0 ? /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
          "line",
          {
            x1: left,
            y1: yScale(highlightValue),
            x2: left + plotWidth,
            y2: yScale(highlightValue),
            stroke: COLORS.gray,
            strokeDasharray: "6 6",
            strokeWidth: "2"
          }
        ) : null,
        secondaryPath ? /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("path", { d: secondaryPath, fill: "none", stroke: secondaryAccent, strokeWidth: "4" }) : null,
        /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("path", { d: path, fill: "none", stroke: accent, strokeWidth: "4" }),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("circle", { cx: xScale(markerEpoch), cy: yScale(values[markerEpoch]), r: "5", fill: COLORS.orange }),
        secondaryValues ? /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("circle", { cx: xScale(markerEpoch), cy: yScale(secondaryValues[markerEpoch]), r: "5", fill: secondaryAccent }) : null
      ] }),
      secondaryValues ? /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "mini-chart__legend", children: [
        /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { style: { color: accent }, children: "Train" }),
        /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { style: { color: secondaryAccent }, children: "Val" })
      ] }) : null
    ] });
  }
  function Figure12Overfitting() {
    const [markerEpoch, setMarkerEpoch] = (0, import_react3.useState)(5);
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)(
      FigureCard,
      {
        kicker: "Figure 12",
        title: "Overfitting Diagnostics",
        subtitle: "Validation stops improving almost immediately while physics parameters continue drifting to extremes.",
        controls: /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("label", { className: "slider-control", children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { children: [
            "Inspect epoch: ",
            markerEpoch
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("input", { type: "range", min: "0", max: "10", value: markerEpoch, onChange: (event) => setMarkerEpoch(Number(event.target.value)) })
        ] }),
        footer: /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "figure-footer-note", children: [
          "Best validation epoch is ",
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "5" }),
          " with ",
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "MAE = 1.929" }),
          "."
        ] }),
        children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "overfit-grid", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
              MiniLineChart,
              {
                title: "A. Train vs Val MAE",
                values: overfitTrain,
                secondaryValues: overfitVal,
                yDomain: [0.15, 2.05],
                markerEpoch,
                accent: COLORS.blue,
                secondaryAccent: COLORS.red,
                note: "Train keeps falling; validation bottoms out at epoch 5."
              }
            ),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
              MiniLineChart,
              {
                title: "B. tau_reg_raw",
                values: overfitTau,
                yDomain: [0, 3],
                markerEpoch,
                highlightValue: 3,
                accent: COLORS.orange,
                note: "NRTL params become extreme."
              }
            ),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
              MiniLineChart,
              {
                title: "C. sol_fraction",
                values: overfitSol,
                yDomain: [0.75, 1],
                markerEpoch,
                highlightValue: 0.5,
                accent: COLORS.blue,
                note: "Still above the minimum, but trending down."
              }
            )
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "overfit-summary", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
              "Train sol_raw: ",
              overfitTrain[markerEpoch].toFixed(3)
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
              "Val MAE: ",
              overfitVal[markerEpoch].toFixed(3)
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
              "tau_reg_raw: ",
              overfitTau[markerEpoch].toFixed(2)
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { children: [
              "sol_fraction: ",
              overfitSol[markerEpoch].toFixed(3)
            ] })
          ] })
        ]
      }
    );
  }
  function Figure13Comparison() {
    const [mode, setMode] = (0, import_react3.useState)("heatmap");
    const radarMetrics = [
      "Acc",
      "T-extra",
      "Interp",
      "Consist",
      "Cost"
    ];
    const radarModels = [
      { name: "RF", color: COLORS.green, values: [4, 0.5, 0.3, 0.3, 4] },
      { name: "DirectGNN", color: COLORS.yellow, values: [2.3, 0.4, 0.5, 0.5, 3] },
      { name: "TGNN-D", color: COLORS.blue, values: [4, 3.5, 4, 4, 2.2] }
    ];
    const heatmapRows = [
      ["RF (desc)", "\u25CF\u25CF\u25CF\u25CF", "\u25CB\u25CB\u25CB\u25CB", "\u25CB\u25CB\u25CB\u25CB", "\u25CB\u25CB\u25CB\u25CB", "\u25CF\u25CF\u25CF\u25CF"],
      ["DirectGNN", "\u25CF\u25CF\u25CB\u25CB", "\u25CB\u25CB\u25CB\u25CB", "\u25CB\u25CB\u25CB\u25CB", "\u25CB\u25CB\u25CB\u25CB", "\u25CF\u25CF\u25CF\u25CB"],
      ["TGNN (current)", "\u25CF\u25CF\u25CB\u25CB", "\u25CF\u25CF\u25CF\u25CB", "\u25CF\u25CF\u25CF\u25CF", "\u25CF\u25CF\u25CF\u25CF", "\u25CF\u25CF\u25CB\u25CB"],
      ["TGNN + desc (exp.)", "\u25CF\u25CF\u25CF\u25CF", "\u25CF\u25CF\u25CF\u25CB", "\u25CF\u25CF\u25CF\u25CF", "\u25CF\u25CF\u25CF\u25CF", "\u25CF\u25CF\u25CB\u25CB"],
      ["UNIFAC", "\u25CF\u25CF\u25CF\u25CB", "\u25CF\u25CF\u25CF\u25CF", "\u25CF\u25CF\u25CF\u25CF", "\u25CF\u25CF\u25CF\u25CF", "\u25CF\u25CF\u25CF\u25CF"],
      ["COSMO-RS", "\u25CF\u25CF\u25CF\u25CB", "\u25CF\u25CF\u25CF\u25CF", "\u25CF\u25CF\u25CF\u25CB", "\u25CF\u25CF\u25CF\u25CF", "\u25CF\u25CB\u25CB\u25CB"]
    ];
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
      FigureCard,
      {
        kicker: "Figure 13",
        title: "Comparison Table",
        subtitle: "The visual summary is easiest to read as either a radar overlay or a Harvey-ball matrix.",
        controls: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
          ToggleGroup,
          {
            label: "Comparison mode",
            options: [
              { label: "Radar", value: "radar" },
              { label: "Heatmap", value: "heatmap" }
            ],
            value: mode,
            onChange: setMode
          }
        ),
        children: mode === "radar" ? /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "comparison-radar-layout", children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "comparison-radar-card", children: /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("svg", { viewBox: "0 0 360 300", role: "img", "aria-label": "Model comparison radar chart", children: [
            Array.from({ length: 4 }, (_, ring) => {
              const radius = 34 + ring * 20;
              const points = radarMetrics.map((_2, index) => {
                const angle = 360 / radarMetrics.length * index;
                const point = polarToCartesian(170, 150, radius, angle);
                return `${point.x},${point.y}`;
              });
              return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("polygon", { points: points.join(" "), fill: "none", stroke: COLORS.line, strokeWidth: "1.6" }, radius);
            }),
            radarMetrics.map((metric, index) => {
              const angle = 360 / radarMetrics.length * index;
              const point = polarToCartesian(170, 150, 110, angle);
              const anchor = point.x < 154 ? "end" : point.x > 186 ? "start" : "middle";
              const dx = point.x < 154 ? -8 : point.x > 186 ? 8 : 0;
              const dy = point.y < 126 ? -8 : point.y > 174 ? 10 : 0;
              return /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("g", { children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("line", { x1: "170", y1: "150", x2: point.x, y2: point.y, stroke: COLORS.line, strokeWidth: "1.6" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                  "text",
                  {
                    x: point.x + dx,
                    y: point.y + dy,
                    textAnchor: anchor,
                    dominantBaseline: "middle",
                    fontSize: "12",
                    fill: DECK_TEXT,
                    fontWeight: "700",
                    children: metric
                  }
                )
              ] }, metric);
            }),
            radarModels.map((model) => {
              const points = model.values.map((value, index) => {
                const angle = 360 / radarMetrics.length * index;
                const point = polarToCartesian(170, 150, 34 + value / 4 * 60, angle);
                return `${point.x},${point.y}`;
              });
              return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                "polygon",
                {
                  points: points.join(" "),
                  fill: model.color,
                  fillOpacity: "0.18",
                  stroke: model.color,
                  strokeWidth: "3"
                },
                model.name
              );
            })
          ] }) }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "comparison-radar-side", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "comparison-radar-note", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "Reading guide" }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("p", { children: "Higher is better on every axis. Accuracy and training cost are inverted before plotting so outer polygons always mean the more desirable trade-off." })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(FigureLegend, { items: radarModels.map((model) => ({ label: model.name, color: model.color })) })
          ] })
        ] }) : /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("table", { className: "comparison-matrix", children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("thead", { children: /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("tr", { children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("th", { children: "Model" }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("th", { children: "Accuracy" }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("th", { children: "T-extrap" }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("th", { children: "Interpret" }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("th", { children: "Consist" }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("th", { children: "Speed" })
          ] }) }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("tbody", { children: heatmapRows.map((row) => /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("tr", { children: row.map((cell) => /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("td", { children: cell }, `${row[0]}-${cell}`)) }, row[0])) })
        ] })
      }
    );
  }
  function Figure14MasterEquation() {
    const examples = [
      { key: "naphthalene", name: "Naphthalene / benzene", phi: 1.2, gamma: 0.02, label: "Nearly ideal" },
      { key: "paracetamol", name: "Paracetamol / ethanol", phi: 2.6, gamma: 0.54, label: "Moderate" },
      { key: "hexane", name: "Paracetamol / hexane", phi: 2.6, gamma: 8.9, label: "Very low" }
    ];
    const [selectedKey, setSelectedKey] = (0, import_react3.useState)("paracetamol");
    const selected = examples.find((item) => item.key === selectedKey) ?? examples[1];
    const total = -(selected.phi + selected.gamma);
    const width = 760;
    const xScale = (value) => 80 + (value + 15) / 15 * 580;
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
      FigureCard,
      {
        kicker: "Figure 14",
        title: "Master Equation",
        subtitle: "Two interpretable penalties add on a single log-solubility axis.",
        controls: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
          ToggleGroup,
          {
            label: "Example pair",
            options: [
              { label: "Naph / benzene", value: "naphthalene" },
              { label: "Para / ethanol", value: "paracetamol" },
              { label: "Para / hexane", value: "hexane" }
            ],
            value: selectedKey,
            onChange: setSelectedKey
          }
        ),
        children: /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "equation-grid equation-grid--rebuilt", children: [
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "equation-header-card", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexBlock, { children: "\\ln x_2 = -\\Phi - \\ln\\gamma_2" }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("p", { className: "figure-subnote", children: "Two interpretable penalties push the solution left on the same log-solubility axis: crystal resistance first, solvent mismatch second." })
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "equation-main equation-main--wide", children: [
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "equation-axis-card", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("svg", { viewBox: `0 0 ${width} 260`, role: "img", "aria-label": "Master equation visual explanation", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("defs", { children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("marker", { id: "equation-blue-arrow", viewBox: "0 0 10 10", refX: "7", refY: "5", markerWidth: "5", markerHeight: "5", orient: "auto", children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("path", { d: "M 0 0 L 10 5 L 0 10 z", fill: COLORS.blue }) }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("marker", { id: "equation-red-arrow", viewBox: "0 0 10 10", refX: "7", refY: "5", markerWidth: "5", markerHeight: "5", orient: "auto", children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("path", { d: "M 0 0 L 10 5 L 0 10 z", fill: COLORS.red }) })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("rect", { x: "54", y: "28", width: "630", height: "176", rx: "18", fill: PAPER_FILL }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("line", { x1: "80", y1: "148", x2: "660", y2: "148", stroke: PAPER_TEXT, strokeWidth: "4", strokeLinecap: "round" }),
                [-15, -12, -9, -6, -3, 0].map((tick) => /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("g", { children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("line", { x1: xScale(tick), y1: "137", x2: xScale(tick), y2: "159", stroke: PAPER_TEXT, strokeWidth: "2" }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("text", { x: xScale(tick), y: "180", textAnchor: "middle", fontSize: "14", fill: PAPER_SOFT_TEXT, children: tick })
                ] }, tick)),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                  "path",
                  {
                    d: `M ${xScale(0)} 86 L ${xScale(-selected.phi)} 86`,
                    fill: "none",
                    stroke: COLORS.blue,
                    strokeWidth: "4.8",
                    strokeLinecap: "round",
                    markerEnd: "url(#equation-blue-arrow)"
                  }
                ),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(
                  "path",
                  {
                    d: `M ${xScale(-selected.phi)} 122 L ${xScale(total)} 122`,
                    fill: "none",
                    stroke: COLORS.red,
                    strokeWidth: "4.8",
                    strokeLinecap: "round",
                    markerEnd: "url(#equation-red-arrow)"
                  }
                ),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("line", { x1: xScale(total), y1: "122", x2: xScale(total), y2: "148", stroke: COLORS.green, strokeWidth: "2.5", strokeDasharray: "5 4" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("circle", { cx: xScale(total), cy: "148", r: "9", fill: COLORS.green }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("text", { x: "86", y: "198", fontSize: "12", fill: PAPER_SOFT_TEXT, children: "very low solubility" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("text", { x: "560", y: "198", fontSize: "12", fill: PAPER_SOFT_TEXT, children: "fully miscible" })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "equation-summary-strip", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "equation-summary-item", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "Crystal term" }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: selected.phi.toFixed(2) })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "equation-summary-item", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "Interaction term" }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: selected.gamma.toFixed(2) })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "equation-summary-item equation-summary-item--final", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: "Final ln x\u2082" }),
                  /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("span", { children: [
                    total.toFixed(2),
                    " \xB7 ",
                    selected.label
                  ] })
                ] })
              ] })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "equation-contrib", children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "equation-contrib__card equation-contrib__card--blue", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "-\\Phi" }) }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "Crystal penalty" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("small", { children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "T_m,\\ \\Delta H,\\ \\Delta C_p" }) })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "equation-contrib__card equation-contrib__card--red", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "-\\ln\\gamma_2" }) }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "Interaction penalty" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("small", { children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "\\tau_{12},\\ \\tau_{21},\\ \\alpha" }) })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: "equation-contrib__card equation-contrib__card--green", children: [
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: "\\ln x_2" }) }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: "Resulting log-solubility" }),
                /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("small", { children: selected.label })
              ] })
            ] })
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", { className: "equation-example-list", children: examples.map((example) => {
            const value = -(example.phi + example.gamma);
            return /* @__PURE__ */ (0, import_jsx_runtime3.jsxs)("div", { className: `equation-example${selectedKey === example.key ? " is-active" : ""}`, children: [
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("strong", { children: example.name }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: `\\Phi \\approx ${example.phi}` }) }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: `\\ln\\gamma_2 \\approx ${example.gamma}` }) }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("span", { children: /* @__PURE__ */ (0, import_jsx_runtime3.jsx)(TexInline, { children: `\\ln x_2 \\approx ${value.toFixed(1)}` }) }),
              /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("small", { children: example.label })
            ] }, example.key);
          }) })
        ] })
      }
    );
  }
  var PRESENTATION_FIGURES = [
    {
      slug: "data-pipeline",
      title: "Data Pipeline",
      subtitle: "Sources \u2192 Merge & Enrich \u2192 Split",
      blurb: "Four heterogeneous sources merge into a sparse, scaffold-safe supervised dataset.",
      tags: ["data", "sparsity", "split"],
      component: Figure1DataPipeline
    },
    {
      slug: "molecular-featurization",
      title: "Molecular Featurization",
      subtitle: "SMILES \u2192 2D structure \u2192 graph",
      blurb: "Canonical SMILES become a molecular graph with typed atom and bond features.",
      tags: ["rdkit", "graph", "features"],
      component: Figure2Featurization
    },
    {
      slug: "pretraining",
      title: "Pretraining",
      subtitle: "Optional Stage 0 before the curriculum",
      blurb: "The repository includes a standalone Stage 0 that pretrains the encoder and readout with four molecular objectives.",
      tags: ["stage0", "contrastive", "pretrain"],
      component: FigurePretraining
    },
    {
      slug: "architecture",
      title: "TGNN-Solv Architecture",
      subtitle: "Five swim lanes from graphs to `ln x\u2082_final`",
      blurb: "The core figure shows where learning ends and where hardcoded thermodynamics begin.",
      tags: ["architecture", "physics", "solver"],
      component: Figure3Architecture
    },
    {
      slug: "matched-baseline",
      title: "Matched Baseline",
      subtitle: "Same backbone, different prediction head",
      blurb: "This slide isolates the main research comparison: TGNN-Solv versus DirectGNN on a shared upstream chemistry stack.",
      tags: ["baseline", "directgnn", "fairness"],
      component: Figure3ABaseline
    },
    {
      slug: "solver-diagnostics",
      title: "Solver-Facing Diagnostics",
      subtitle: "Raw outputs, substituted outputs, exported intermediates",
      blurb: "The maintained forward API makes GC priors, oracle injection, and solver-facing tensors inspectable instead of hidden.",
      tags: ["diagnostics", "oracle", "intermediates"],
      component: Figure3BDiagnostics
    },
    {
      slug: "sle-solver",
      title: "SLE Solver",
      subtitle: "Fixed-point geometry and contraction",
      blurb: "The solver iterates to a root quickly enough that implicit gradients are attractive.",
      tags: ["solver", "fixed-point", "nrtl"],
      component: Figure4Solver
    },
    {
      slug: "implicit-diff",
      title: "Implicit Differentiation",
      subtitle: "Against unrolled backprop",
      blurb: "One backward step replaces an O(N) chain of stored solver iterations.",
      tags: ["training", "backprop", "memory"],
      component: Figure5Backprop
    },
    {
      slug: "loss-landscape",
      title: "Loss Landscape",
      subtitle: "12 components before and after the `vant_hoff_local` fix",
      blurb: "The optimizer only behaves once solubility regains the dominant share of Phase 2 loss.",
      tags: ["loss", "optimization", "curriculum"],
      component: Figure6LossLandscape
    },
    {
      slug: "linear-probe",
      title: "Linear Probe",
      subtitle: "Where descriptor information disappears",
      blurb: "Probe scores show that the encoder, not physics, dominates the current accuracy gap.",
      tags: ["probe", "descriptors", "bottleneck"],
      component: Figure7LinearProbe
    },
    {
      slug: "error-decomposition",
      title: "Error Decomposition",
      subtitle: "Waterfall from RF to TGNN",
      blurb: "Most measured error increase comes from the GNN representation gap rather than the solver bottleneck.",
      tags: ["mae", "waterfall", "gap"],
      component: Figure8Waterfall
    },
    {
      slug: "temperature-extrapolation",
      title: "Temperature Extrapolation",
      subtitle: "Why the physics path matters out of range",
      blurb: "Physics-guided temperature dependence remains meaningful where tabular models flatten out.",
      tags: ["temperature", "extrapolation", "schematic"],
      component: Figure9TemperatureExtrapolation
    },
    {
      slug: "curriculum",
      title: "Three-Phase Curriculum",
      subtitle: "What trains when",
      blurb: "Curriculum structure controls solver activation, correction unfreezing, and oracle annealing.",
      tags: ["curriculum", "training", "schedule"],
      component: Figure10Curriculum
    },
    {
      slug: "gc-priors",
      title: "GC Priors",
      subtitle: "Bounded residuals around group contribution estimates",
      blurb: "GC priors shrink the crystal-property search space before the model spends capacity on residuals.",
      tags: ["gc", "priors", "crystal"],
      component: Figure11GCPriors
    },
    {
      slug: "overfitting",
      title: "Overfitting Diagnostics",
      subtitle: "Train/val divergence and parameter drift",
      blurb: "Validation degrades while NRTL regularization pressure rises and solubility share falls.",
      tags: ["overfit", "diagnostics", "tau"],
      component: Figure12Overfitting
    },
    {
      slug: "comparison-table",
      title: "Comparison Table",
      subtitle: "Trade-offs across model families",
      blurb: "The deck can switch between a radar overlay and a matrix for slide-friendly comparison.",
      tags: ["comparison", "trade-offs", "positioning"],
      component: Figure13Comparison
    },
    {
      slug: "master-equation",
      title: "Master Equation",
      subtitle: "`ln x\u2082 = -\u03A6 - ln \u03B3\u2082` as a picture",
      blurb: "Two interpretable penalties add on one axis, which makes prediction outputs explainable by construction.",
      tags: ["equation", "interpretability", "physics"],
      component: Figure14MasterEquation
    }
  ];

  // src/slide-notes.jsx
  var import_react4 = __toESM(require_react(), 1);
  var import_jsx_runtime4 = __toESM(require_jsx_runtime(), 1);
  function TexInline2({ children }) {
    return /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("span", { className: "tex-inline", children: `\\(${children}\\)` });
  }
  function TexBlock2({ children }) {
    return /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("div", { className: "tex-block", children: `\\[${children}\\]` });
  }
  var NOTES_BY_SLUG = {
    "data-pipeline": {
      summary: "What this slide means",
      content: /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
        /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("p", { children: [
          "The builder turns heterogeneous raw sources into one sparse supervision matrix. Conceptually the training set is a table ",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "\\mathcal D = \\{(s_i, v_i, T_i, y_i, z_i)\\}" }),
          ", where solubility",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "y_i = \\ln x_{2,i}" }),
          " is dense but auxiliary targets ",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "z_i" }),
          " are mostly missing."
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("p", { children: [
          "The key visual point is that missingness is structural, not an error: each auxiliary column has a mask",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "m_{ij} \\in \\{0,1\\}" }),
          ". The scaffold split then enforces that the same solute core does not appear in both train and test."
        ] })
      ] }),
      report: /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "In report terms, this figure justifies why the training loop is multi-task but mask-aware. The model sees one merged schema, while every auxiliary head only contributes where the corresponding supervision bit is present, so sparsity becomes a planned design constraint rather than a data-quality failure." })
    },
    "molecular-featurization": {
      summary: "How SMILES becomes tensors",
      content: /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
        /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("p", { children: [
          "The molecule is first parsed into a graph ",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "G = (V, E)" }),
          ". Each atom gets a feature vector",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "x_a \\in \\mathbb R^{35}" }),
          ", and each bond gets a feature vector",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "e_{ab} \\in \\mathbb R^{8}" }),
          "."
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "The interactive panel makes that mapping explicit: click an atom or bond, and the card on the right shows the corresponding symbolic features together with one small slice of the learned numeric representation." })
      ] }),
      report: /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "The practical reason to show this explicitly is that every downstream claim about TGNN-Solv starts here. If the graph abstraction drops chemically relevant local cues, neither the solver nor auxiliary supervision can recover that information later, because they only operate on the encoded representation they receive." })
    },
    pretraining: {
      summary: "How Stage 0 works in this repository",
      content: /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
        /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "`src/tgnn_solv/pretrain.py` implements a standalone pre-curriculum Stage 0. It is explicitly separate from Phase 1 in `trainer.py`: Stage 0 uses large SMILES collections, updates `model.gnn` and `model.readout` in place, and then discards its temporary heads before normal TGNN training begins." }),
        /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("p", { children: [
          "The code trains four objectives together: masked 2-hop subgraph reconstruction, masked bond-type prediction, RDKit descriptor regression, and graph-level contrastive learning. The combined objective is",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "L = L_{atom} + 0.5L_{bond} + L_{prop} + 0.5L_{ctr}" }),
          " with default temperature",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "\\tau = 0.1" }),
          "."
        ] })
      ] }),
      report: /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "The intended payoff is not a separate benchmark, but a chemically sharper initialization for the main curriculum. Stage 0 teaches local topology, graph-level invariances, and descriptor-aligned global semantics before the architecture has to solve the much harder supervised SLE problem on sparse thermodynamic labels." })
    },
    architecture: {
      summary: "Where learning stops and physics starts",
      content: /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
        /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("p", { children: [
          "The encoder and interaction stack learn molecular representations, but the final prediction is not produced by a free MLP. Instead, the model assembles a pair state",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "g_{pair} = [g_{sol} \\parallel g_{slv} \\parallel g_{sol}\\odot g_{slv} \\parallel |g_{sol}-g_{slv}|]" }),
          "and turns it into thermodynamic parameters."
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("p", { children: [
          "The red zone is the point of the architecture: once ",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "T_m, \\Delta H_{fus}, \\tau_{12}, \\tau_{21}, \\alpha" }),
          "are predicted, the hardcoded SLE solver determines ",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "\\ln x_2" }),
          ". That is the physics bottleneck."
        ] })
      ] }),
      report: /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "That separation is the core modeling claim of the project. The network is allowed to learn latent chemistry, but it is not allowed to invent an unconstrained mapping from embeddings to solubility; instead it must explain the prediction through physically interpretable intermediate quantities." })
    },
    "matched-baseline": {
      summary: "Why this comparison is considered fair",
      content: /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
        /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("p", { children: [
          "The repository\u2019s maintained comparison is explicitly controlled. Both models use the same upstream chemistry stack, so the ablation is not ",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "f_{TGNN} \\text{ vs } g_{other}" }),
          " in the abstract, but rather the same encoder and interaction layers with two different output heads."
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("p", { children: [
          "In shorthand, TGNN-Solv predicts solver-facing thermodynamic parameters and returns",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "\\ln x_2 = \\mathrm{SLE}(\\theta) + \\text{bounded correction}" }),
          ", while DirectGNN predicts",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "\\ln x_2" }),
          " directly from the same pair representation plus temperature encoding."
        ] })
      ] }),
      report: /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "This distinction matters for interpretation of every downstream benchmark. If TGNN underperforms or overperforms relative to DirectGNN, the result can be attributed mainly to the physics bottleneck and its constraints, rather than to a hidden difference in graph capacity, interaction depth, or readout family." })
    },
    "solver-diagnostics": {
      summary: "What `model.forward(...)` exposes for analysis",
      content: /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
        /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("p", { children: [
          "The forward path does not collapse everything into one opaque prediction. It keeps raw head outputs such as",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("code", { children: "fusion_params" }),
          " separate from ",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("code", { children: "solver_fusion_params" }),
          ", the actual values passed into the solver after GC-prior substitution or optional oracle replacement."
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("p", { children: [
          "With ",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("code", { children: "return_intermediates=True" }),
          ", the model also exports solver-facing tensors like",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "\\Phi,\\ \\ln\\gamma_2,\\ \\ln x_{2,physics},\\ \\ln x_{2,final}" }),
          ". That makes it possible to diagnose whether an error came from crystal inputs, interaction parameters, solver geometry, or the correction branch."
        ] })
      ] }),
      report: /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "From a project-maintenance perspective, this is one of the most important documented surfaces in the repository. It turns train-time mechanisms such as oracle injection from implicit behavior into explicit exported state, which is why the evaluation and full-budget experiment scripts can produce defensible diagnostic artifacts instead of only final MAE numbers." })
    },
    "sle-solver": {
      summary: "Why the iteration converges quickly",
      content: /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
        /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("p", { children: [
          "The solver applies a fixed-point map",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexBlock2, { children: "x_2^{(k+1)} = \\lambda e^{-\\Phi - \\ln\\gamma_2(x_2^{(k)})} + (1-\\lambda)x_2^{(k)}" }),
          "until the iterate stabilizes."
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("p", { children: [
          "The left panel is zoomed into the only region that matters numerically. Because the local slope is small,",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "|g'(x_2^*)| \\ll 1" }),
          ", the orange cobweb contracts to the green root in a few steps."
        ] })
      ] }),
      report: /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "The important reading is not the exact synthetic numbers, but the geometry of the map near the solution. A stable contraction means forward solve time stays low, implicit gradients become attractive, and the solver can remain a hardcoded layer instead of turning into another fragile learned recurrent block." })
    },
    "implicit-diff": {
      summary: "Why implicit gradients are preferred",
      content: /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
        /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("p", { children: [
          "Unrolled differentiation stores every solver step and backpropagates through the whole chain, which costs",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "\\mathcal O(N)" }),
          " memory and multiplies many local Jacobians."
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("p", { children: [
          "Implicit differentiation instead uses the converged fixed point directly:",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexBlock2, { children: "\\frac{d x_2^*}{d\\theta} = -\\frac{\\partial F / \\partial \\theta}{\\partial F / \\partial x_2^*}" }),
          "so backward becomes a one-step correction around the solution."
        ] })
      ] }),
      report: /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "In other words, the method trades iteration-history bookkeeping for local analytical structure at the solution. That reduces memory pressure, removes long chains of fragile Jacobian products, and matches the fact that only the converged root matters for the final loss." })
    },
    "loss-landscape": {
      summary: "What changed after the loss fix",
      content: /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
        /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("p", { children: [
          "Training optimizes a weighted sum ",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "L = \\sum_j \\lambda_j L_j" }),
          ". If one component dominates the total scale, the optimizer effectively ignores the rest."
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "The left plot shows that `vant_hoff_local` was swallowing the objective; the right plot shows the intended regime, where solubility again owns most of the gradient budget and the auxiliary terms stay secondary." })
      ] }),
      report: /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "This slide is therefore an optimization diagnosis, not only a cosmetic rebalance. If `L_sol` is numerically tiny compared with the rest, the model can appear to train while effectively not learning the target task that matters most for the paper, namely solubility prediction itself." })
    },
    "linear-probe": {
      summary: "How to read the probe scores",
      content: /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
        /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("p", { children: [
          "Each bar is a linear-probe score for one descriptor. The metric is",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "R^2 = 1 - \\frac{\\sum (y - \\hat y)^2}{\\sum (y - \\bar y)^2}" }),
          ", so larger values mean the encoder retained that descriptor more faithfully."
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "This slide argues that the present error gap is mostly representational. If a descriptor is only weakly recoverable from the encoder state, the downstream physics path never gets a clean enough starting point." })
      ] }),
      report: /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "That is why the probe matters strategically. It separates a solver bottleneck from an encoder bottleneck: if the latent state does not linearly expose descriptor information that is known to be useful, improving the physics head alone will have limited payoff because the missing signal has already been lost upstream." })
    },
    "error-decomposition": {
      summary: "What the waterfall is attributing",
      content: /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
        /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("p", { children: [
          "The bars are additive gaps relative to the best descriptor baseline. In shorthand,",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "\\Delta \\mathrm{MAE} = \\mathrm{MAE}_{model} - \\mathrm{MAE}_{RF}" }),
          "."
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "The important interpretation is not the exact number on each bar, but the split of responsibility: most of the current degradation appears before the solver, inside the molecular representation itself." })
      ] }),
      report: /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "Put differently, the waterfall turns a vague underperformance statement into an engineering prioritization. If the largest gap is representational, the next experiments should focus on encoder enrichment, descriptor augmentation, and pretraining rather than replacing the thermodynamic solver." })
    },
    "temperature-extrapolation": {
      summary: "Why the physics path extrapolates differently",
      content: /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
        /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("p", { children: [
          "Outside the observed temperature range, a generic tabular regressor often defaults toward local averages. The TGNN path remains structured because the solver imposes an explicit temperature law through ",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "\\Phi(T)" }),
          "."
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("p", { children: [
          "A useful mental model is the van't Hoff slope:",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "\\frac{d\\ln x_2}{dT} \\approx \\frac{\\Delta H_{sol}}{RT^2}" }),
          ". The exact implementation is more detailed, but the key point is that temperature dependence is encoded, not guessed."
        ] })
      ] }),
      report: /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "The slide is schematic on purpose: it communicates expected behavior, not a final benchmark panel. The message is that physics earns its keep precisely where interpolation ends, because the solver imposes a structured trend that remains meaningful beyond the temperatures seen during fitting." })
    },
    curriculum: {
      summary: "Why the schedule is staged",
      content: /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
        /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("p", { children: [
          "Early in training, the model is not ready to run the whole physics stack stably. Phase 1 therefore keeps solubility off, roughly as ",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "w_{sol}(t)=0" }),
          ", while property heads warm up."
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "Phase 2 activates the full solver path, and Phase 3 lowers the learning rate for refinement. The visual point is that solver activation, correction unfreezing, and oracle annealing are coordinated rather than simultaneous." })
      ] }),
      report: /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "This is effectively a stabilization protocol for a heterogeneous model. The schedule controls when fragile pieces are allowed to move, so the encoder, auxiliary heads, solver-facing parameters, and correction branch do not all start drifting before their upstream signals are even sensible." })
    },
    "gc-priors": {
      summary: "What the prior is buying you",
      content: /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
        /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("p", { children: [
          "Instead of predicting crystal properties from scratch, the model learns a bounded residual:",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexBlock2, { children: "T_m = T_m^{GC} + \\delta, \\qquad |\\delta| \\le 50\\,K" })
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "That changes optimization geometry. The head no longer searches the full physically plausible interval; it only has to correct the prior locally, which is why the search window on the right is dramatically narrower." })
      ] }),
      report: /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "From a training perspective, this is a variance-reduction device. A decent group-contribution anchor removes a large low-frequency burden from the crystal head, so learned capacity is spent on bounded residual structure instead of rediscovering first-order thermochemistry from sparse labels." })
    },
    overfitting: {
      summary: "How to read the overfitting signal",
      content: /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
        /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("p", { children: [
          "The three panels track validation quality, parameter drift, and objective balance together. The useful scalar is the best epoch",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "t^* = \\arg\\min_t \\mathrm{MAE}_{val}(t)" }),
          ", which appears very early."
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("p", { children: [
          "After that point, train loss keeps improving, but validation stalls while ",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "\\tau_{reg}" }),
          " rises. That combination suggests the model is using extra freedom to fit training noise rather than improving physical generalization."
        ] })
      ] }),
      report: /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "The three traces are shown together because no single metric is sufficient on its own. Validation MAE indicates usefulness, `tau_reg` indicates whether NRTL parameters are drifting into aggressive regimes, and `sol_fraction` shows whether the optimizer is still spending enough attention on the main target." })
    },
    "comparison-table": {
      summary: "How to interpret the positioning slide",
      content: /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
        /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("p", { children: [
          "This slide is not an absolute benchmark table; it is a compact trade-off view. Each model is summarized by a small score vector ",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "r \\in [0,4]^5" }),
          " over accuracy, extrapolation, interpretability, consistency, and speed."
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "The radar view emphasizes geometry of trade-offs, while the matrix view emphasizes readability on dense slides. Both are meant to answer the same question: what is gained when physics is inserted into the prediction path?" })
      ] }),
      report: /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "This makes the slide useful in discussion, because it compresses a multi-objective argument into one panel. The intended conclusion is not that TGNN dominates every baseline on every axis today, but that it occupies a different operating point where interpretability and extrapolation are built into the prediction path." })
    },
    "master-equation": {
      summary: "The equation behind the whole model",
      content: /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
        /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("p", { children: [
          "The central decomposition is",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexBlock2, { children: "\\ln x_2 = -\\Phi - \\ln\\gamma_2" }),
          "where ",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "-\\Phi" }),
          " is the crystal-side melting penalty and",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "-\\ln\\gamma_2" }),
          " is the solvent-side interaction penalty."
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("p", { children: [
          "The axis view is useful because both effects act on the same scalar coordinate. Equivalently,",
          /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "x_2 = \\exp(-\\Phi - \\ln\\gamma_2)" }),
          ", so either a worse crystal term or a worse interaction term pushes solubility downward in one additive log-space picture."
        ] })
      ] }),
      report: /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "As a report summary, this is the cleanest mental model for TGNN-Solv. The network is learning two physically interpretable penalties whose sum determines the final prediction, which is exactly why the model can support explanation, diagnostics, and controlled extrapolation better than a direct black-box regressor." })
    }
  };
  var EXTRA_NOTES_BY_SLUG = {
    "data-pipeline": /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
      /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("p", { children: [
        "From an engineering perspective, this merged table is the reason the training code has to carry masks all the way into the loss. A row may supervise ",
        /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "\\ln x_2" }),
        " only, crystal properties only, or a mixed subset, so the model is effectively trained on a partially observed multi-task matrix rather than on a clean dense label tensor."
      ] }),
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "The split policy matters just as much as the merge policy. If related scaffolds leaked across train and test, the evaluation would partly measure memorization of chemotypes already seen during fitting, whereas the maintained scaffold split gives a harder but more defensible estimate of generalization to new solute cores." })
    ] }),
    "molecular-featurization": /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "The key implementation detail is that the graph retains chemically typed local structure, not just connectivity. Atom tensors encode hybridization, charge, aromaticity, ring membership, and simple physicochemical scalars, while bond tensors preserve order, conjugation, ring status, and stereochemical flags." }),
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "This is why the slide is interactive rather than decorative. The viewer can move directly from a visible atom or bond to the exact local representation that the encoder consumes, which turns the featurization step into something auditable instead of a hidden preprocessing black box." })
    ] }),
    pretraining: /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "Stage 0 should be read as representation shaping, not as a replacement for the three-phase curriculum. It is designed to teach the encoder invariances and chemically meaningful summary signals before the supervised TGNN objectives begin competing for capacity on a much smaller and much sparser thermodynamic dataset." }),
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "The four tasks are complementary in that they stress different scales of information. Masked subgraphs and bond prediction enforce local chemistry, descriptor regression enforces molecule-level semantics, and contrastive learning encourages stable graph summaries under mild perturbations of the same underlying molecule." })
    ] }),
    architecture: /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "Weight sharing in the encoder is a deliberate constraint. Solute and solvent play different thermodynamic roles downstream, but the model still benefits from a common molecular representation language at the graph level, which keeps parameter count controlled and reduces the chance that each branch learns incompatible latent conventions." }),
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "The more important architectural choice is where the model is not flexible. Once the learned modules emit solver-facing quantities, the prediction path becomes structured, which means later analysis can ask whether an error came from the encoder, from crystal-property estimation, from interaction parameters, or from the correction branch." })
    ] }),
    "matched-baseline": /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
      /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("p", { children: [
        "The baseline should therefore be read as a matched ablation rather than as an external competitor from a different design family. DirectGNN removes ",
        /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("code", { children: "FusionHead" }),
        ", ",
        /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("code", { children: "NRTLHead" }),
        ", ",
        /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("code", { children: "SLESolver" }),
        ", and",
        /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("code", { children: "AdaptivePhysicsCorrection" }),
        ", but it keeps the same upstream representation machinery that converts molecules into a pair state."
      ] }),
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "This is also why descriptor augmentation on the DirectGNN side remains informative rather than unfair. The descriptor branch augments the pair representation after the shared graph backbone, so it probes whether missing chemistry signal is better supplied by richer features or by the explicit thermodynamic bottleneck." })
    ] }),
    "solver-diagnostics": /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "This slide connects the code surface to the experimental surface. Because the forward pass preserves raw predictions, solver-facing substitutions, correction outputs, and oracle masks explicitly, the repository can export intermediate CSV/JSON artifacts that are interpretable after training instead of only reporting scalar aggregate metrics." }),
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "It also clarifies why GC priors and oracle injection are not the same thing. GC priors change how crystal predictions are parameterized, whereas oracle injection conditionally replaces selected supervised solver inputs during training or diagnostics; keeping these paths separate in the returned tensors avoids conceptual and implementation ambiguity." })
    ] }),
    "sle-solver": /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "In implementation terms, the fixed-point loop is the bridge between learned parameters and thermodynamic consistency. The network does not directly output solubility; instead it outputs quantities that define the map whose root corresponds to the physically admissible solution." }),
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "That distinction matters for stability and interpretation. A direct regressor can always fit a number, but a structured solver can fail or contract depending on the local geometry, so this slide is really explaining why the maintained parameterization is numerically tame enough to keep the hardcoded layer practical." })
    ] }),
    "implicit-diff": /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "The backward story is as important as the forward story here. If gradients were propagated only through a finite unroll, the result would depend on an arbitrary truncation horizon and would inherit all the instability of repeated Jacobian products over the iteration chain." }),
      /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("p", { children: [
        "Implicit differentiation instead treats the converged state as the object of interest. That matches the training objective more closely, because the loss depends on the settled solution ",
        /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(TexInline2, { children: "x_2^*" }),
        ", not on the transient path the solver used to get there, and it explains why memory use can stay essentially constant in the number of solver steps."
      ] })
    ] }),
    "loss-landscape": /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "The before/after comparison is therefore a diagnosis of effective objective weighting. Even if YAML weights look reasonable on paper, the optimizer only responds to the scale it actually sees after all reductions, masks, and batching effects have been applied inside the training loop." }),
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "Once solubility regains the majority share of the total loss, the auxiliary terms return to their intended role: they regularize and stabilize representation learning without hijacking the experiment. That is why this slide belongs in a report about model behavior, not only in a debugging appendix." })
    ] }),
    "linear-probe": /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "Linear probes are useful precisely because they are weak models. If a descriptor cannot be recovered linearly from the latent state, then the information is either missing or encoded in a far less accessible form than a downstream head would ideally need for robust prediction and transfer." }),
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "The strategic implication is that descriptor augmentation and pretraining are not cosmetic add-ons. They are direct attempts to reduce the representational deficit exposed by the probe, which is why this slide connects naturally to both the pretraining slide and the descriptor-gap slides later in the deck." })
    ] }),
    "error-decomposition": /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "The RF baseline is not presented as the final desired model family; it is used here as a high-signal reference point because it sees strong fixed descriptors directly. That makes it a practical way to separate chemistry-representation losses from later losses introduced by the physics bottleneck." }),
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "In report terms, the waterfall is really a prioritization chart. If nearly all of the gap appears before the solver, then the next cycle of work should focus on richer graph representations, pretraining, or descriptor fusion before spending large effort on redesigning the thermodynamic layer." })
    ] }),
    "temperature-extrapolation": /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "This panel should be read as an inductive-bias argument. A model without embedded temperature physics has no reason to preserve the qualitative shape of a solubility curve outside the observed window, whereas the TGNN path inherits a structured dependence through the solver-facing thermodynamic terms." }),
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "The note about pending quantitative results is important. The purpose of the slide is to explain why the physics bottleneck is expected to help out-of-range behavior, not to overclaim measured superiority on a benchmark that the project has not yet fully finalized for this exact visualization." })
    ] }),
    curriculum: /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "The schedule is effectively a control system for optimization difficulty. Different parts of the architecture have very different failure modes, so staggering their activation prevents early noise in one branch from destabilizing the rest of the model before any meaningful representation has formed." }),
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "This also explains why the phases should not be collapsed into a single training regime by default. Simultaneous activation of solver, correction, auxiliary losses, and oracle-like supports would make it much harder to attribute improvements or failures to a specific mechanism during experiments." })
    ] }),
    "gc-priors": /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "Bounded residual learning changes the optimization problem from global search to local correction. Instead of asking the crystal head to discover an entire physically plausible interval from sparse supervision, the model begins from a chemically motivated estimate and only learns how to shift it within a controlled band." }),
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "The practical interpretation is that prior quality now matters in a measurable way. If the GC estimate is already close, the residual branch can focus on systematic bias; if it is poor, the bound still prevents the head from drifting into implausible values while the rest of the architecture continues training." })
    ] }),
    overfitting: /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "A useful way to read this slide is as a three-signal consensus check. Validation MAE alone tells you when performance peaks, but not why; the auxiliary traces reveal whether the model is becoming too confident in aggressive NRTL settings or whether the loss budget is slowly shifting away from the main target." }),
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "That is why early stopping in this project should be informed by diagnostics rather than by a single scalar alone. A small change in validation error might be easy to dismiss, but if it arrives together with rising regularization pressure and weakening solubility focus, the combined picture is much more convincing evidence of overfitting." })
    ] }),
    "comparison-table": /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "The radar and matrix views are complementary communication tools rather than competing scientific claims. The radar emphasizes geometry and trade-off shape for presentations, while the matrix sacrifices some visual drama in exchange for cleaner reading when many model families must be compared at once." }),
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "The underlying ratings are deliberately coarse. They should be interpreted as a positioning summary grounded in the repository\u2019s current evidence and modeling intent, not as a substitute for the detailed benchmark tables and experiment logs elsewhere in the documentation and results folders." })
    ] }),
    "master-equation": /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(import_jsx_runtime4.Fragment, { children: [
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "The reason this decomposition is so useful is that it turns one prediction into two interpretable penalties. In log space, additive structure is especially convenient: a worse crystal term or a worse interaction term simply shifts the same scalar outcome leftward, making diagnosis and explanation far more direct." }),
      /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { children: "That also clarifies the project\u2019s modeling philosophy. TGNN-Solv is not trying to learn an opaque map from molecules and temperature to solubility; it is trying to learn the physically meaningful ingredients whose sum determines solubility, which is why the architecture can support explanation and controlled extrapolation more naturally than a direct black-box predictor." })
    ] })
  };
  function readInitialOpenState() {
    if (typeof window === "undefined") {
      return false;
    }
    const params = new URLSearchParams(window.location.search);
    return params.get("notes") === "1";
  }
  function SlideNotes({ slug }) {
    const [isOpen, setIsOpen] = (0, import_react4.useState)(readInitialOpenState);
    const contentRef = (0, import_react4.useRef)(null);
    const panelId = (0, import_react4.useId)();
    const note = NOTES_BY_SLUG[slug];
    const extra = EXTRA_NOTES_BY_SLUG[slug];
    (0, import_react4.useEffect)(() => {
      setIsOpen(readInitialOpenState());
    }, [slug]);
    (0, import_react4.useEffect)(() => {
      if (!isOpen || !contentRef.current || typeof window === "undefined") {
        return;
      }
      if (window.MathJax?.typesetPromise) {
        window.MathJax.typesetPromise([contentRef.current]).catch(() => {
        });
      }
    }, [isOpen, slug]);
    if (!note) {
      return null;
    }
    return /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("section", { className: `slide-notes${isOpen ? " is-open" : ""}`, children: [
      /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)(
        "button",
        {
          type: "button",
          className: "slide-notes__toggle",
          "aria-expanded": isOpen,
          "aria-controls": panelId,
          onClick: () => setIsOpen((previous) => !previous),
          children: [
            /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("span", { className: "slide-notes__title", children: "Slide Notes" }),
            /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("span", { className: "slide-notes__summary", children: note.summary }),
            /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("span", { className: "slide-notes__chevron", children: isOpen ? "Hide" : "Show" })
          ]
        }
      ),
      isOpen ? /* @__PURE__ */ (0, import_jsx_runtime4.jsxs)("div", { id: panelId, ref: contentRef, className: "slide-notes__content", children: [
        /* @__PURE__ */ (0, import_jsx_runtime4.jsx)("p", { className: "slide-notes__lead", children: "This note expands the slide into a short report section: what the figure is claiming, how it maps to the maintained TGNN-Solv implementation, and what conclusion the viewer should take away from it." }),
        note.content,
        note.report,
        extra
      ] }) : null
    ] });
  }

  // src/app.jsx
  var import_jsx_runtime5 = __toESM(require_jsx_runtime(), 1);
  function readInitialIndex() {
    if (typeof window === "undefined") {
      return 0;
    }
    const hash = window.location.hash.replace(/^#/, "");
    const figureIndex = PRESENTATION_FIGURES.findIndex((figure) => figure.slug === hash);
    return figureIndex >= 0 ? figureIndex : 0;
  }
  function PresentationApp() {
    return /* @__PURE__ */ (0, import_jsx_runtime5.jsx)(PresentationDataProvider, { children: /* @__PURE__ */ (0, import_jsx_runtime5.jsx)(PresentationDeck, {}) });
  }
  function PresentationDeck() {
    const [activeIndex, setActiveIndex] = (0, import_react5.useState)(readInitialIndex);
    const activeFigure = PRESENTATION_FIGURES[activeIndex];
    const FigureComponent = activeFigure.component;
    const presentationData = usePresentationData();
    (0, import_react5.useEffect)(() => {
      const onHashChange = () => {
        const nextIndex = readInitialIndex();
        setActiveIndex(nextIndex);
      };
      const onKeyDown = (event) => {
        if (event.key === "ArrowRight" || event.key === "PageDown") {
          event.preventDefault();
          (0, import_react5.startTransition)(() => {
            setActiveIndex((previous) => Math.min(PRESENTATION_FIGURES.length - 1, previous + 1));
          });
        }
        if (event.key === "ArrowLeft" || event.key === "PageUp") {
          event.preventDefault();
          (0, import_react5.startTransition)(() => {
            setActiveIndex((previous) => Math.max(0, previous - 1));
          });
        }
      };
      window.addEventListener("hashchange", onHashChange);
      window.addEventListener("keydown", onKeyDown);
      return () => {
        window.removeEventListener("hashchange", onHashChange);
        window.removeEventListener("keydown", onKeyDown);
      };
    }, []);
    (0, import_react5.useEffect)(() => {
      if (typeof window === "undefined") {
        return;
      }
      const nextHash = `#${activeFigure.slug}`;
      if (window.location.hash !== nextHash) {
        window.history.replaceState(null, "", nextHash);
      }
    }, [activeFigure.slug]);
    (0, import_react5.useEffect)(() => {
      if (typeof window === "undefined") {
        return void 0;
      }
      let timeoutId;
      const root = document.getElementById("tgnn-presentation-root");
      const typeset = () => {
        if (!root) {
          return;
        }
        if (window.MathJax?.typesetPromise) {
          window.MathJax.typesetPromise([root]).catch(() => {
          });
        }
      };
      if (window.MathJax?.typesetPromise) {
        window.requestAnimationFrame(typeset);
      } else {
        timeoutId = window.setTimeout(typeset, 900);
      }
      return () => {
        if (timeoutId) {
          window.clearTimeout(timeoutId);
        }
      };
    }, [activeIndex]);
    const goToIndex = (nextIndex) => {
      (0, import_react5.startTransition)(() => {
        setActiveIndex(clampIndex(nextIndex));
      });
    };
    return /* @__PURE__ */ (0, import_jsx_runtime5.jsxs)("div", { className: "tgnn-presentation-page", children: [
      /* @__PURE__ */ (0, import_jsx_runtime5.jsxs)("section", { className: "presentation-hero", children: [
        /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("div", { className: "presentation-hero__eyebrow", children: "Interactive research deck" }),
        /* @__PURE__ */ (0, import_jsx_runtime5.jsxs)("div", { className: "presentation-hero__copy", children: [
          /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("h1", { children: "TGNN-Solv Presentation" }),
          /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("p", { children: "A slide-like React application embedded directly into the MkDocs site. The deck covers the data pipeline, baselines, architecture, solver mechanics, diagnostics, optimization behavior, and the current accuracy gap." })
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime5.jsxs)("div", { className: "presentation-hero__stats", children: [
          /* @__PURE__ */ (0, import_jsx_runtime5.jsxs)("div", { children: [
            /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("strong", { children: PRESENTATION_FIGURES.length }),
            /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("span", { children: "figures" })
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime5.jsxs)("div", { children: [
            /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("strong", { children: "React" }),
            /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("span", { children: "embedded in MkDocs" })
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime5.jsxs)("div", { children: [
            /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("strong", { children: formatGeneratedAt(presentationData.meta.generatedAt) }),
            /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("span", { children: presentationData.meta.source === "manifest" ? "auto-fed metrics" : "fallback metrics" })
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime5.jsxs)("div", { children: [
            /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("strong", { children: "Keyboard" }),
            /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("span", { children: "\u2190 / \u2192 to navigate" })
          ] })
        ] })
      ] }),
      /* @__PURE__ */ (0, import_jsx_runtime5.jsxs)("div", { className: "presentation-strip", children: [
        /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("div", { className: "presentation-strip__title", children: "Deck map" }),
        /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("nav", { className: "presentation-strip__nav", "aria-label": "Presentation figures", children: PRESENTATION_FIGURES.map((figure, index) => /* @__PURE__ */ (0, import_jsx_runtime5.jsxs)(
          "button",
          {
            type: "button",
            className: `presentation-strip__item${index === activeIndex ? " is-active" : ""}`,
            onClick: () => goToIndex(index),
            children: [
              /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("span", { className: "presentation-strip__count", children: String(index + 1).padStart(2, "0") }),
              /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("span", { className: "presentation-strip__text", children: figure.title })
            ]
          },
          figure.slug
        )) })
      ] }),
      /* @__PURE__ */ (0, import_jsx_runtime5.jsxs)("main", { className: "presentation-stage", children: [
        /* @__PURE__ */ (0, import_jsx_runtime5.jsxs)("header", { className: "presentation-stage__header", children: [
          /* @__PURE__ */ (0, import_jsx_runtime5.jsxs)("div", { children: [
            /* @__PURE__ */ (0, import_jsx_runtime5.jsxs)("div", { className: "presentation-stage__meta", children: [
              "Slide ",
              activeIndex + 1,
              " / ",
              PRESENTATION_FIGURES.length
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("h2", { children: activeFigure.title }),
            /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("p", { children: activeFigure.blurb })
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime5.jsxs)("div", { className: "presentation-stage__actions", children: [
            /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("button", { type: "button", className: "nav-button", onClick: () => goToIndex(activeIndex - 1), disabled: activeIndex === 0, children: "Prev" }),
            /* @__PURE__ */ (0, import_jsx_runtime5.jsx)(
              "button",
              {
                type: "button",
                className: "nav-button nav-button--primary",
                onClick: () => goToIndex(activeIndex + 1),
                disabled: activeIndex === PRESENTATION_FIGURES.length - 1,
                children: "Next"
              }
            )
          ] })
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("div", { className: "presentation-stage__tags", children: activeFigure.tags.map((tag) => /* @__PURE__ */ (0, import_jsx_runtime5.jsx)("span", { className: "presentation-tag", children: tag }, tag)) }),
        /* @__PURE__ */ (0, import_jsx_runtime5.jsx)(FigureComponent, {}),
        /* @__PURE__ */ (0, import_jsx_runtime5.jsx)(SlideNotes, { slug: activeFigure.slug })
      ] })
    ] });
  }
  function clampIndex(index) {
    return Math.min(PRESENTATION_FIGURES.length - 1, Math.max(0, index));
  }
  function formatGeneratedAt(value) {
    if (!value) {
      return "Auto data";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return "Auto data";
    }
    return new Intl.DateTimeFormat("en", {
      month: "short",
      day: "numeric"
    }).format(date);
  }

  // src/main.jsx
  var import_jsx_runtime6 = __toESM(require_jsx_runtime(), 1);
  function mountPresentation() {
    const rootElement = document.getElementById("tgnn-presentation-root");
    if (!rootElement || rootElement.dataset.mounted === "true") {
      return;
    }
    rootElement.dataset.mounted = "true";
    document.body.classList.add("tgnn-presentation-route");
    const root = (0, import_client.createRoot)(rootElement);
    root.render(/* @__PURE__ */ (0, import_jsx_runtime6.jsx)(PresentationApp, {}));
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mountPresentation, { once: true });
  } else {
    mountPresentation();
  }
})();
/*! Bundled license information:

react/cjs/react.production.min.js:
  (**
   * @license React
   * react.production.min.js
   *
   * Copyright (c) Facebook, Inc. and its affiliates.
   *
   * This source code is licensed under the MIT license found in the
   * LICENSE file in the root directory of this source tree.
   *)

scheduler/cjs/scheduler.production.min.js:
  (**
   * @license React
   * scheduler.production.min.js
   *
   * Copyright (c) Facebook, Inc. and its affiliates.
   *
   * This source code is licensed under the MIT license found in the
   * LICENSE file in the root directory of this source tree.
   *)

react-dom/cjs/react-dom.production.min.js:
  (**
   * @license React
   * react-dom.production.min.js
   *
   * Copyright (c) Facebook, Inc. and its affiliates.
   *
   * This source code is licensed under the MIT license found in the
   * LICENSE file in the root directory of this source tree.
   *)

react/cjs/react-jsx-runtime.production.min.js:
  (**
   * @license React
   * react-jsx-runtime.production.min.js
   *
   * Copyright (c) Facebook, Inc. and its affiliates.
   *
   * This source code is licensed under the MIT license found in the
   * LICENSE file in the root directory of this source tree.
   *)
*/
