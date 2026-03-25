import React, { useState, useEffect, useRef } from 'react';
import { supabase } from './supabaseClient';
import './index.css';

const APP_VERSION = 'v1.0.3'; // HER GÜNCELLEMEDE ARTIR
const API_BASE_URL = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? "" : `http://${window.location.hostname}:8000`);
const ADMIN_EMAIL = 'admin@admin.com'; // Burayi kendi e-postanla degistirebilirsin

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [user, setUser] = useState(null);
  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState('Dashboard');
  const [onlineUsers, setOnlineUsers] = useState([]);
  const [suggestions, setSuggestions] = useState([]); // Arama önerileri
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [trackedSymbols, setTrackedSymbols] = useState([]); // Kullanıcının aradığı hisseler
  const [favoriteSymbols, setFavoriteSymbols] = useState([]); // Favori hisseler
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [authMode, setAuthMode] = useState('login'); // 'login' or 'signup'
  
  // Auth Form State
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [authError, setAuthError] = useState('');

  // Admin State
  const [users, setUsers] = useState([]);
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [adminStats, setAdminStats] = useState({ cached_financials: 0, total_users: 0, online_users: 0 });
  const [cachedStocks, setCachedStocks] = useState([]);
  const [showCachedList, setShowCachedList] = useState(false);

  // Supabase Auth Session
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        setUser(session.user);
        setIsLoggedIn(true);
      }
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session) {
        setUser(session.user);
        setIsLoggedIn(true);
      } else {
        setUser(null);
        setIsLoggedIn(false);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const handleLogin = async (e) => {
    e.preventDefault();
    setAuthError('');
    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      if (error) throw error;
      // Session handling will happen in onAuthStateChange
    } catch (err) {
      setAuthError(err.message || 'Giriş hatası');
    }
  };

  const handleSignUp = async (e) => {
    e.preventDefault();
    setAuthError('');
    try {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
      });
      if (error) throw error;
      alert('Kayıt başarılı! Lütfen e-postanızı onaylayın (eğer açıksa) veya giriş yapın.');
      setAuthMode('login');
    } catch (err) {
      setAuthError(err.message || 'Kayıt hatası');
    }
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
    localStorage.removeItem('storedUser');
  };

  const fetchUsers = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/users`);
      if (response.ok) {
        const data = await response.json();
        if (Array.isArray(data)) {
          setUsers(data);
        } else {
          console.error("Beklenmeyen veri formatı:", data);
          setUsers([]);
        }
      } else {
        console.error("Kullanıcı listesi alınamadı:", response.status);
      }
    } catch (err) {
      console.error("User fetch error:", err);
    }
  };

  const handleDeleteUser = async (username) => {
    if (!confirm(`${username} kullanıcısını silmek istediğinize emin misiniz?`)) {
      return;
    }
    
    try {
      const response = await fetch(`${API_BASE_URL}/admin/users/${username}`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        alert(`${username} kullanıcısı başarıyla silindi.`);
        fetchUsers(); // Listeyi yenile
        fetchAdminStats(); // İstatistikleri güncelle
      } else {
        const error = await response.json();
        alert(`Hata: ${error.detail || 'Kullanıcı silinemedi'}`);
      }
    } catch (err) {
      console.error("Delete user error:", err);
      alert("Kullanıcı silinirken bir hata oluştu.");
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    if (!newUsername || !newPassword) {
      alert("Kullanıcı adı ve şifre gereklidir.");
      return;
    }
    
    try {
      const response = await fetch(`${API_BASE_URL}/admin/create-user`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: newUsername,
          password: newPassword,
        }),
      });
      
      if (response.ok) {
        alert(`${newUsername} kullanıcısı başarıyla oluşturuldu.`);
        setNewUsername('');
        setNewPassword('');
        fetchUsers(); // Listeyi yenile
        fetchAdminStats(); // İstatistikleri güncelle
      } else {
        const error = await response.json();
        alert(`Hata: ${error.detail || 'Kullanıcı oluşturulamadı'}`);
      }
    } catch (err) {
      console.error("Create user error:", err);
      alert("Kullanıcı oluşturulurken bir hata oluştu.");
    }
  };

  useEffect(() => {
    if (activeTab === 'Admin') {
      fetchUsers();
      fetchAdminStats();
    }
  }, [activeTab]);

  const fetchAdminStats = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/stats`);
      if (response.ok) {
        const data = await response.json();
        setAdminStats(data);
      }
    } catch (err) {
      console.error("Stats fetch error:", err);
    }
  };

  const fetchCachedStocks = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/admin/cached-stocks`);
      if (response.ok) {
        const data = await response.json();
        setCachedStocks(data);
        setShowCachedList(true);
      }
    } catch (err) {
      console.error("Cached stocks fetch error:", err);
    }
  };

  useEffect(() => {
    if (!isLoggedIn || !user) return;
    
    const sendHeartbeat = async () => {
      try {
        // Backend GET beklediği için GET yapıyoruz
        await fetch(`${API_BASE_URL}/heartbeat`, {
          method: 'GET'
        });
      } catch (err) {}
    };

    const fetchOnlineUsers = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/admin/online-users`);
        if (response.ok) {
          const data = await response.json();
          if (Array.isArray(data)) {
            setOnlineUsers(data);
          }
        }
      } catch (err) {}
    };

    sendHeartbeat();
    fetchOnlineUsers();

    const hInterval = setInterval(sendHeartbeat, 30000);
    const oInterval = setInterval(fetchOnlineUsers, 10000);

    return () => {
      clearInterval(hInterval);
      clearInterval(oInterval);
    };
  }, [isLoggedIn, user]);

  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const observerTarget = React.useRef(null);
  const [activeStock, setActiveStock] = useState(null); // Detay görünümü için seçili hisse

  // ... (Login ve User Fetch kodları aynı)

  // Stokları Çekme (Sayfalı)
  useEffect(() => {
    if (!isLoggedIn) return;
    
    const fetchStocks = async () => {
      // Eğer sayfa 1 ise yükleniyor göster, değilse background yükleme
      if (page === 1) setLoading(true);
      
      try {
        const symbolsParam = '';
        const limit = 15;
        const response = await fetch(`${API_BASE_URL}/stocks?page=${page}&limit=${limit}${symbolsParam}`);
        const result = await response.json();
        
        // Yeni backend yapısı: { items: [], has_more: true/false }
        // Eski yapı (array) gelirse diye fallback
        const data = Array.isArray(result) ? result : (result.items || []);
        const serverHasMore = result.has_more !== undefined ? result.has_more : (data.length >= limit);

        setHasMore(serverHasMore);

        setStocks(prev => {
          if (page === 1) return data;
          
          // Duplicate kontrolü
          const newStocks = [...prev];
          data.forEach(item => {
            if (!newStocks.find(s => s.symbol === item.symbol)) {
              newStocks.push(item);
            }
          });
          return newStocks;
        });
        
        setLoading(false);
      } catch (error) {
        console.error("API Error:", error);
        setLoading(false);
      }
    };

    fetchStocks();
  }, [isLoggedIn, page, trackedSymbols]); // page değişince tetiklenir

  // Infinite Scroll Observer
  useEffect(() => {
    const observer = new IntersectionObserver(
      entries => {
        if (entries[0].isIntersecting && hasMore && !loading) {
           setPage(prev => prev + 1);
        }
      },
      { threshold: 1.0 }
    );

    if (observerTarget.current) {
      observer.observe(observerTarget.current);
    }

    return () => {
      if (observerTarget.current) {
        observer.unobserve(observerTarget.current);
      }
    };
  }, [hasMore, loading]);


  // Manuel Arama Reset
  const handleManualSearch = async (forcedSymbol = null) => {
    const targetSymbol = forcedSymbol || searchTerm.trim();
    if (!targetSymbol) return;
    
    // Aramada sayfayı başa sar ve arananı tracked'e ekle
    setPage(1);
    setHasMore(true);
    
    const symbol = targetSymbol.toUpperCase();
    setShowSuggestions(false);
    
    setTrackedSymbols(prev => {
        const cleanSymbol = symbol.replace('.IS', ''); // Temizle
        const filtered = prev.filter(s => s !== cleanSymbol && s !== symbol);
        return [cleanSymbol, ...filtered].slice(0, 20);
    });
    setSearchTerm('');
    setActiveStock(symbol.replace('.IS', '')); // Detay sayfasını aç
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };


  // Favoriler Yükleme (Supabase)
  useEffect(() => {
    if (user) {
      const fetchFavorites = async () => {
        const { data, error } = await supabase
          .from('favorites')
          .select('symbol')
          .eq('user_id', user.id);
        
        if (!error && data) {
          setFavoriteSymbols(data.map(f => f.symbol));
        }
      };
      fetchFavorites();
    }
  }, [user]);

  // Favoriler Kaydetme (Supabase'e taşındığı için gerek kalmadı ama boş bırakalım)
  useEffect(() => {
    // Supabase ile her toggle'da direkt DB'ye yazıyoruz.
  }, [favoriteSymbols, user]);

  // Favori Ekle/Çıkar (Supabase)
  const toggleFavorite = async (symbol, e) => {
    if(e) e.stopPropagation();
    if (!user) return;

    if (favoriteSymbols.includes(symbol)) {
      setFavoriteSymbols(prev => prev.filter(s => s !== symbol));
      await supabase
        .from('favorites')
        .delete()
        .eq('user_id', user.id)
        .eq('symbol', symbol);
    } else {
      setFavoriteSymbols(prev => [...prev, symbol]);
      await supabase
        .from('favorites')
        .insert([{ user_id: user.id, symbol: symbol }]);
    }
  };

  const getDisplayStocks = () => {
    let source = stocks || [];
    
    // Eğer favoriler sekmesindeysek sadece favorileri filtrele
    if (activeTab === 'Favorites') {
      source = source.filter(s => favoriteSymbols.includes(s.symbol));
    }

    return source.filter(stock => 
      stock && stock.symbol && (
        stock.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (stock.name && stock.name.toLowerCase().includes(searchTerm.toLowerCase()))
      )
    );
  };

  // Kullanıcı değiştiğinde kayıtlı geçmişi yükle
  useEffect(() => {
    // Takip edilen hisseler şimdilik local'de kalabilir veya ileride Supabase'e taşınabilir
    if (user) {
      const storageKey = `tracked_symbols_${user.id || user}`;
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        try {
          setTrackedSymbols(JSON.parse(saved));
        } catch (e) {
          setTrackedSymbols([]);
        }
      }
    }
  }, [user]);

  // Takip listesi değiştiğinde kaydet
  useEffect(() => {
    if (user) {
      localStorage.setItem(`tracked_symbols_${user}`, JSON.stringify(trackedSymbols));
    }
  }, [trackedSymbols, user]);

  // Arama Önerilerini Çek
  useEffect(() => {
    let active = true;
    
    const fetchSuggestions = async () => {
      if (searchTerm.trim().length < 2) {
        if (active) setSuggestions([]);
        return;
      }
      try {
        const response = await fetch(`${API_BASE_URL}/search/suggestions?q=${searchTerm}`);
        if (response.ok) {
          const data = await response.json();
          if (active) {
            setSuggestions(Array.isArray(data) ? data : []);
          }
        }
      } catch (err) {
        console.error("Suggestion fetch error:", err);
      }
    };

    const timeoutId = setTimeout(fetchSuggestions, 300); // Debounce
    return () => {
      active = false;
      clearTimeout(timeoutId);
    };
  }, [searchTerm]);

  if (!isLoggedIn) {
    return (
      <div className="login-container">
        <div className="login-box">
          <div className="logo" style={{ textAlign: 'center', marginBottom: '2rem', letterSpacing: '0px' }}>
            PhD TERMİNAL
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.5rem', fontWeight: 'normal' }}>{APP_VERSION}</div>
          </div>
          <form onSubmit={authMode === 'login' ? handleLogin : handleSignUp}>
            <div className="form-group">
              <label>E-posta</label>
              <input 
                type="email" 
                className="search-bar" 
                style={{ width: '100%' }}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="form-group" style={{ marginTop: '1rem' }}>
              <label>Şifre</label>
              <input 
                type="password" 
                className="search-bar" 
                style={{ width: '100%' }}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            {authError && <p style={{ color: 'var(--loss-color)', marginTop: '0.5rem', fontSize: '0.8rem' }}>{authError}</p>}
            <button type="submit" className="login-btn">
              {authMode === 'login' ? 'Giriş Yap' : 'Kayıt Ol'}
            </button>
            
            <div style={{ marginTop: '1.5rem', textAlign: 'center', fontSize: '0.9rem' }}>
              {authMode === 'login' ? (
                <p>Hesabınız yok mu? <span onClick={() => setAuthMode('signup')} style={{ color: 'var(--accent-color)', cursor: 'pointer' }}>Kayıt Olun</span></p>
              ) : (
                <p>Zaten hesabınız var mı? <span onClick={() => setAuthMode('login')} style={{ color: 'var(--accent-color)', cursor: 'pointer' }}>Giriş Yapın</span></p>
              )}
            </div>
          </form>
        </div>
      </div>
    );
  }




  const displayedStocks = getDisplayStocks();

  return (
    <div className="app-container">
      <aside className={`sidebar ${isSidebarCollapsed ? 'collapsed' : ''}`}>
        <button className="toggle-btn" onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}>
          {isSidebarCollapsed ? '>' : '<'}
        </button>
        <div className="logo" style={{ letterSpacing: '0px', whiteSpace: 'nowrap' }}>
          PhD {!isSidebarCollapsed && 'TERMİNAL'}
          <div style={{ fontSize: '0.7rem', color: 'var(--accent-color)', marginTop: '0.2rem', fontWeight: 'normal' }}>{APP_VERSION}</div>
        </div>
        <nav>
          <ul className="nav-links">
            <li className={`nav-item ${activeTab === 'Dashboard' ? 'active' : ''}`} onClick={() => { setActiveTab('Dashboard'); setActiveStock(null); }}>
              <i className="nav-icon">🏠</i>
              <span>Dashboard</span>
            </li>
            <li className={`nav-item ${activeTab === 'Favorites' ? 'active' : ''}`} onClick={() => { setActiveTab('Favorites'); setActiveStock(null); }}>
              <i className="nav-icon">⭐</i>
              <span>Favoriler</span>
            </li>
            <li className={`nav-item ${activeTab === 'TemelAnaliz' ? 'active' : ''}`} onClick={() => { setActiveTab('TemelAnaliz'); setActiveStock(null); }}>
              <i className="nav-icon">📊</i>
              <span>Temel analiz</span>
            </li>
            <li className={`nav-item ${activeTab === 'Degerleme' ? 'active' : ''}`} onClick={() => { setActiveTab('Degerleme'); setActiveStock(null); }}>
              <i className="nav-icon">💰</i>
              <span>Değerleme</span>
            </li>
            <li className={`nav-item ${activeTab === 'TeknikAnaliz' ? 'active' : ''}`} onClick={() => { setActiveTab('TeknikAnaliz'); setActiveStock(null); }}>
              <i className="nav-icon">📈</i>
              <span>Teknik analiz</span>
            </li>
            <li className={`nav-item ${activeTab === 'TakasAnalizi' ? 'active' : ''}`} onClick={() => { setActiveTab('TakasAnalizi'); setActiveStock(null); }}>
              <i className="nav-icon">🔄</i>
              <span>Takas analizi</span>
            </li>
            <li className={`nav-item ${activeTab === 'SektorAnalizi' ? 'active' : ''}`} onClick={() => { setActiveTab('SektorAnalizi'); setActiveStock(null); }}>
              <i className="nav-icon">🏭</i>
              <span>Sektör analizi</span>
            </li>
            {user?.email === ADMIN_EMAIL && (
              <li className={`nav-item ${activeTab === 'Admin' ? 'active' : ''}`} onClick={() => setActiveTab('Admin')}>
                <i className="nav-icon">⚙️</i>
                <span>Admin Paneli</span>
              </li>
            )}
            <li className="nav-item" onClick={handleLogout}>
               <i className="nav-icon">🚪</i>
               <span>Çıkış Yap</span>
            </li>
          </ul>
        </nav>
      </aside>

      <div className="online-panel">
        <h4 style={{fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '1rem', paddingLeft: '0.5rem'}}>ONLINE</h4>
        <div className="online-list">
          {Array.isArray(onlineUsers) && onlineUsers.map(u => (
            <div key={u} className="online-user-item">
              <span className="online-dot shine"></span>
              <span className="online-name" title={u}>{u.split('@')[0]}</span>
            </div>
          ))}
        </div>
      </div>

      <main className="main-content">
        {activeTab === 'Admin' && user?.email === ADMIN_EMAIL ? (
          <div className="admin-view">
            <h1>Admin Paneli</h1>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>Kayıtlı kullanıcıları yönetin ve yenilerini ekleyin.</p>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem', marginBottom: '2rem' }}>
               <div 
                 className="stock-card" 
                 onClick={fetchCachedStocks}
                 style={{ textAlign: 'center', padding: '1.5rem', cursor: 'pointer', border: showCachedList ? '1px solid var(--accent-color)' : '1px solid rgba(255,255,255,0.1)' }}
               >
                 <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>MAALİ TABLOSU ÇEKİLEN HİSSELER</div>
                 <div style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--accent-color)' }}>{adminStats.cached_financials}</div>
                 <div style={{ fontSize: '0.7rem', color: 'var(--accent-color)', marginTop: '5px' }}>{showCachedList ? '[-] Listeyi Gizle' : '[+] Listeyi Gör'}</div>
               </div>
               <div className="stock-card" style={{ textAlign: 'center', padding: '1.5rem' }}>
                 <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>TOPLAM KULLANICI</div>
                 <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{adminStats.total_users}</div>
               </div>
               <div className="stock-card" style={{ textAlign: 'center', padding: '1.5rem' }}>
                 <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>ONLİNE KULLANICI</div>
                 <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#00ff00' }}>{adminStats.online_users}</div>
               </div>
             </div>

             {showCachedList && (
               <div className="stock-card" style={{ marginBottom: '2rem', animation: 'fadeIn 0.3s ease' }}>
                 <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                   <h3 style={{ margin: 0 }}>Hafızadaki Hisseler ({cachedStocks.length})</h3>
                   <button onClick={() => setShowCachedList(false)} style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}>Kapat [x]</button>
                 </div>
                 <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(100px, 1fr))', gap: '10px' }}>
                    {cachedStocks.map(s => (
                      <button 
                        key={s} 
                        onClick={() => { setActiveStock(s); setActiveTab('Dashboard'); }}
                        className="badge" 
                        style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', cursor: 'pointer', padding: '8px', textAlign: 'center' }}
                      >
                        {s}
                      </button>
                    ))}
                 </div>
               </div>
             )}

             <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: '2rem' }}>
               <div className="stock-card">
                 <h3>Yeni Kullanıcı Ekle</h3>
                 <form onSubmit={handleCreateUser} style={{ marginTop: '1rem' }}>
                   <div className="form-group">
                     <label>Kullanıcı Adı</label>
                     <input 
                       type="text" 
                       className="search-bar" 
                       style={{ width: '100%', marginBottom: '1rem' }}
                       value={newUsername}
                       onChange={(e) => setNewUsername(e.target.value)}
                     />
                   </div>
                   <div className="form-group">
                     <label>Şifre</label>
                     <input 
                       type="password" 
                       className="search-bar" 
                       style={{ width: '100%', marginBottom: '1rem' }}
                       value={newPassword}
                       onChange={(e) => setNewPassword(e.target.value)}
                     />
                   </div>
                   <button type="submit" className="login-btn">Kullanıcıyı Kaydet</button>
                 </form>
               </div>

              <div className="stock-table-container">
                <h3>Kayıtlı Kullanıcılar</h3>
                <table style={{ marginTop: '1rem' }}>
                  <thead>
                    <tr>
                      <th>KULLANICI ADI</th>
                      <th>YETKİ</th>
                      <th>İŞLEM</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((uname) => (
                      <tr key={uname}>
                        <td><strong>{uname}</strong></td>
                        <td>
                          <span className="badge" style={{ color: uname === 'admin' ? 'var(--accent-color)' : 'white' }}>
                            {uname === 'admin' ? 'Admin' : 'Arkadaş'}
                          </span>
                        </td>
                        <td>
                          {uname !== 'admin' && (
                            <button 
                              onClick={() => handleDeleteUser(uname)}
                              style={{
                                background: 'rgba(255, 77, 77, 0.2)',
                                border: '1px solid rgba(255, 77, 77, 0.3)',
                                color: '#ff4d4d',
                                padding: '4px 12px',
                                borderRadius: '6px',
                                cursor: 'pointer',
                                fontSize: '0.75rem',
                                fontWeight: 'bold'
                              }}
                            >
                              🗑️ Sil
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            </div>
            ) : activeStock ? (
                <StockDetailView 
                    symbol={activeStock} 
                    onBack={() => setActiveStock(null)} 
                    toggleFavorite={toggleFavorite}
                    isFavorite={favoriteSymbols.includes(activeStock)}
                />
            ) : (
            <>
            <header>
              <h1>Hoş geldin, {user.email?.split('@')[0]}</h1>
              <div className="search-container" style={{ position: 'relative', width: '100%', maxWidth: '600px', zIndex: 50 }}>
                <div style={{ display: 'flex', gap: '0.5rem', width: '100%' }}>
                  <input 
                    type="text" 
                    className="search-bar" 
                    placeholder="Hisse ara (Örn: nv, karsn, thyao)..." 
                    value={searchTerm}
                    onChange={(e) => {
                      setSearchTerm(e.target.value);
                      setShowSuggestions(true);
                    }}
                    onKeyDown={(e) => e.key === 'Enter' && handleManualSearch()}
                    onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                    style={{ flex: 1 }}
                  />
                  <button 
                    onClick={() => handleManualSearch()}
                    className="login-btn"
                    style={{ width: 'auto', padding: '0 1.5rem', height: '45px', marginTop: 0 }}
                  >
                    Ara
                  </button>
                </div>

                {showSuggestions && suggestions.length > 0 && (
                  <div className="suggestions-dropdown">
                    {suggestions.map((s, idx) => (
                      <div 
                        key={`${s.symbol}-${idx}`} 
                        className="suggestion-item"
                        onClick={() => handleManualSearch(s.symbol)}
                      >
                        <div className="suggestion-info">
                          <span className="suggestion-symbol">{s.symbol}</span>
                          <span className="suggestion-name">{s.name}</span>
                        </div>
                        <span className="suggestion-exchange">{s.exchange}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <small style={{display: 'block', color: 'var(--text-secondary)', marginTop: '0.5rem'}}>
                *Listede olmayan hisseler Yahoo Finance'den anlık çekilir.
              </small>
            </header>

            {loading ? (
              <div className="loading-state">Yükleniyor...</div>
            ) : (
              <>
                <div className="dashboard-grid">
                  {(activeTab === 'Favorites' ? displayedStocks : displayedStocks.slice(0, 3)).map(stock => (
                    <div 
                        key={stock.symbol} 
                        className="stock-card" 
                        style={{position: 'relative', cursor: 'pointer'}}
                        onClick={() => setActiveStock(stock.symbol)}
                    >
                      <button 
                        className="fav-btn"
                        onClick={(e) => toggleFavorite(stock.symbol, e)}
                        style={{
                          position: 'absolute',
                          top: '10px',
                          right: '10px',
                          background: 'none',
                          border: 'none',
                          cursor: 'pointer',
                          color: favoriteSymbols.includes(stock.symbol) ? '#FFD700' : 'var(--text-secondary)',
                          fontSize: '1.2rem',
                          zIndex: 10
                        }}
                      >
                        {favoriteSymbols.includes(stock.symbol) ? '★' : '☆'}
                      </button>
                      <div className="stock-header">
                        <div className="stock-id">
                          <span className="stock-symbol">{stock.symbol.replace('.IS', '')}</span>
                          <div className="stock-name-small">{stock.name}</div>
                        </div>
                        <div style={{textAlign: 'right', marginTop:'20px'}}>
                           <div className={stock.change > 0 ? 'change-up' : stock.change < 0 ? 'change-down' : ''} style={{fontWeight: 'bold', fontSize: '1.2rem'}}>
                              {stock.changePercent}%
                           </div>
                        </div>
                      </div>
                      <div className="stock-price">{stock.price?.toLocaleString()}</div>
                      <div style={{fontSize: '0.8rem', color:'var(--text-secondary)', marginTop:'5px'}}>
                        Açılış: {stock.open ? stock.open.toLocaleString() : '-'}
                      </div>

                    </div>
                  ))}
                </div>

                {activeTab === 'Dashboard' && displayedStocks.length > 3 && (
                    <div className="stock-table-container">
                    <h3>Diğer Geçmiş</h3>
                    {Object.entries(
                        displayedStocks.slice(3).reduce((groups, stock) => {
                            const sector = stock.sector_group || 'Diğer';
                            if (!groups[sector]) groups[sector] = [];
                            groups[sector].push(stock);
                            return groups;
                        }, {})
                    ).map(([sector, stocks]) => (
                        <div key={sector} style={{ marginBottom: '2rem' }}>
                            <h4 style={{ 
                                color: 'var(--accent-color)', 
                                borderBottom: '1px solid var(--border-color)', 
                                paddingBottom: '0.5rem', 
                                marginBottom: '0.5rem',
                                marginTop: '1rem'
                            }}>
                                {sector}
                            </h4>
                            <table style={{ marginTop: '0.5rem' }}>
                            <thead>
                                <tr>
                                <th>SEMBOL</th>
                                <th>AÇILIŞ</th>
                                <th>FİYAT</th>
                                <th>DEĞİŞİM</th>
                                <th>FAVORİ</th> 
                                </tr>
                            </thead>
                            <tbody>
                                {stocks.map(stock => (
                                <tr key={stock.symbol} onClick={() => setActiveStock(stock.symbol)} style={{cursor:'pointer'}}>
                                    <td>
                                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                                        <span className="badge" style={{width: 'fit-content', marginBottom:'4px'}}>{stock.symbol.replace('.IS', '')}</span>
                                        <small style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>{stock.name}</small>
                                    </div>
                                    </td>
                                    <td>{stock.open ? stock.open.toLocaleString() : '-'}</td>
                                    <td>{stock.price?.toLocaleString()}</td>
                                    <td className={stock.change > 0 ? 'change-up' : stock.change < 0 ? 'change-down' : ''}>
                                    <span style={{fontWeight:'bold'}}>{stock.changePercent}%</span>
                                    </td>
                                    <td style={{textAlign: 'center'}}>
                                    <button 
                                        onClick={(e) => toggleFavorite(stock.symbol, e)}
                                        style={{
                                        background: 'transparent',
                                        border: 'none',
                                        color: favoriteSymbols.includes(stock.symbol) ? '#FFD700' : 'var(--text-secondary)',
                                        fontSize: '1.2rem',
                                        cursor: 'pointer'
                                        }}
                                    >
                                        {favoriteSymbols.includes(stock.symbol) ? '★' : '☆'}
                                    </button>
                                    </td>
                                </tr>
                                ))}
                            </tbody>
                            </table>
                        </div>
                    ))}
                    
                    {/* Infinite Scroll Tetikleyici */}
                    <div ref={observerTarget} style={{ height: '20px', margin: '10px 0' }}>
                       {hasMore && !loading && <span style={{color:'var(--text-secondary)', fontSize:'0.8rem'}}>Daha fazla yükleniyor...</span>}
                    </div>

                  </div>
                )}
              </>
            )}
          </>
        )}
      </main>
    </div>
  );
}

function PhDPriceChart({ data }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!data || data.length < 2 || !containerRef.current) return;

    const LightweightCharts = window.LightweightCharts;
    if (!LightweightCharts) return;

    containerRef.current.innerHTML = '';
    const chart = LightweightCharts.createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 500,
      layout: {
        background: { type: 'solid', color: '#131722' },
        textColor: '#d1d4dc',
      },
      grid: {
        vertLines: { color: 'rgba(42, 46, 57, 0.5)' },
        horzLines: { color: 'rgba(42, 46, 57, 0.5)' },
      },
      timeScale: { borderColor: 'rgba(197, 203, 206, 0.8)' },
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: '#26a69a', downColor: '#ef5350', borderVisible: false,
      wickUpColor: '#26a69a', wickDownColor: '#ef5350',
    });

    const formattedData = data
      .filter(d => d.Date && d.Open !== null)
      .map(d => ({
        time: d.Date,
        open: Number(d.Open),
        high: Number(d.High),
        low: Number(d.Low),
        close: Number(d.Close)
      }))
      .sort((a, b) => a.time.localeCompare(b.time));

    if (formattedData.length > 0) {
      candleSeries.setData(formattedData);
      chart.timeScale().fitContent();
    }

    const addMA = (key, color) => {
      const maData = data
        .filter(d => d[key] !== null)
        .map(d => ({ time: d.Date, value: Number(d[key]) }))
        .sort((a, b) => a.time.localeCompare(b.time));
      
      if (maData.length > 0) {
        const lineSeries = chart.addLineSeries({ color, lineWidth: 1, priceLineVisible: false });
        lineSeries.setData(maData);
      }
    };

    addMA('MA20', '#ff9800');
    addMA('MA50', '#2196f3');

    chartRef.current = chart;

    const handleResize = () => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data]);

  if (!data || data.length < 2) {
    return (
      <div style={{ height: '500px', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#131722', borderRadius: '15px', color: 'var(--text-secondary)' }}>
        Grafik verisi yükleniyor veya bulunamadı...
      </div>
    );
  }

  return <div ref={containerRef} style={{ width: '100%', height: '500px', borderRadius: '15px', overflow: 'hidden' }} />;
}

function TradingViewChart({ tvSymbol }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!tvSymbol || !containerRef.current) return;

    containerRef.current.innerHTML = '';
    const cleanSymbol = tvSymbol.replace('BIST:', '').replace('.IS', '');
    
    const iframe = document.createElement('iframe');
    iframe.src = `https://s.tradingview.com/widgetembed/?symbol=BIST%3A${cleanSymbol}&interval=D&hidesidetoolbar=0&symboledit=1&saveimage=1&toolbarbg=f1f3f6&studies=%5B%5D&theme=dark&style=1&timezone=Europe%2FIstanbul&locale=tr`;
    iframe.style.width = '100%';
    iframe.style.height = '100%';
    iframe.style.border = 'none';
    
    containerRef.current.appendChild(iframe);
  }, [tvSymbol]);

  return (
    <div style={{ width: '100%', height: '500px', position: 'relative' }}>
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
      <div style={{ position: 'absolute', bottom: '10px', left: '10px', fontSize: '0.7rem', color: 'rgba(255,255,255,0.3)', pointerEvents: 'none' }}>
        * Veri kısıtlamaları nedeniyle grafik TradingView ana sitesine yönlendirebilir.
      </div>
    </div>
  );
}

function StockDetailView({ symbol, onBack, toggleFavorite, isFavorite }) {
  const [detail, setDetail] = useState(null);
  const [financials, setFinancials] = useState(null);
  const [loading, setLoading] = useState(true);
  const [finLoading, setFinLoading] = useState(true);
  const [p1, setP1] = useState("");
  const [p2, setP2] = useState("");
  const [p3, setP3] = useState("");
  const [p4, setP4] = useState("");
  const [isDescExpanded, setIsDescExpanded] = useState(false);
  const [detailTab, setDetailTab] = useState('Özet');
  const [stockHistory, setStockHistory] = useState([]);
  const [brokerageData, setBrokerageData] = useState(null);
  const [chartMode, setChartMode] = useState('local'); // 'local' or 'tv'

  useEffect(() => {
    const fetchDetail = async () => {
        try {
            const res = await fetch(`${API_BASE_URL}/stocks/${symbol}/detail`);
            if (res.ok) {
                const data = await res.json();
                setDetail(data);
            }
            setLoading(false);
        } catch (e) {
            console.error(e);
            setLoading(false);
        }
    };
    const fetchFinancials = async () => {
        setFinLoading(true);
        try {
            const res = await fetch(`${API_BASE_URL}/stocks/${symbol}/financials`);
            if (res.ok) {
                const data = await res.json();
                setFinancials(data);
                if (data.periods && data.periods.length >= 4) {
                    setP1(data.periods[0]);
                    setP2(data.periods[1]);
                    setP3(data.periods[2]);
                    setP4(data.periods[3]);
                } else if (data.periods && data.periods.length >= 1) {
                    setP1(data.periods[0] || "");
                    setP2(data.periods[1] || "");
                    setP3(data.periods[2] || "");
                    setP4(data.periods[3] || "");
                }
            }
            setFinLoading(false);
        } catch (e) {
            console.error("Financial fetch error:", e);
            setFinLoading(false);
        }
    };
    const fetchHistory = async () => {
        try {
            const res = await fetch(`${API_BASE_URL}/stocks/${symbol}/history?period=1y`);
            if (res.ok) {
                const data = await res.json();
                setStockHistory(data);
            }
        } catch (e) {
            console.error("History fetch error:", e);
        }
    };
    const fetchBrokerage = async () => {
        try {
            const res = await fetch(`${API_BASE_URL}/stocks/${symbol}/brokerage`);
            if (res.ok) {
                const data = await res.json();
                setBrokerageData(data);
            }
        } catch (e) {
            console.error("Brokerage fetch error:", e);
        }
    };

    fetchDetail();
    fetchFinancials();
    fetchHistory();
    fetchBrokerage();
  }, [symbol]);

  if (loading) return <div className="loading-state">Detaylar yükleniyor...</div>;
  if (!detail) return <div className="loading-state">Veri bulunamadı. <button onClick={onBack}>Geri Dön</button></div>;

  const formatLargeNumber = (num) => {
      if (!num) return '-';
      if (num >= 1e9) return (num / 1e9).toFixed(2) + ' Mr';
      if (num >= 1e6) return (num / 1e6).toFixed(2) + ' Mn';
      return num.toLocaleString();
  };

  return (
      <div className="fade-in" style={{ maxWidth: '1000px', margin: '0 auto' }}>
          <button onClick={onBack} style={{ marginBottom: '1rem', background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', display:'flex', alignItems:'center', gap:'5px' }}>
              ← Listeye Dön
          </button>

          {/* Tab Menu */}
          <div style={{ display: 'flex', gap: '10px', marginBottom: '1.5rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '10px' }}>
              {['Özet', 'Temel', 'Değerleme', 'Teknik', 'Takas'].map(tab => (
                  <button
                      key={tab}
                      onClick={() => setDetailTab(tab)}
                      style={{
                          background: detailTab === tab ? 'var(--accent-color)' : 'transparent',
                          color: detailTab === tab ? '#000' : 'var(--text-secondary)',
                          border: 'none',
                          padding: '8px 20px',
                          borderRadius: '20px',
                          cursor: 'pointer',
                          fontSize: '0.9rem',
                          fontWeight: 'bold',
                          transition: 'all 0.3s ease'
                      }}
                  >
                      {tab}
                  </button>
              ))}
          </div>

          {detailTab === 'Özet' && (
              <>
          {/* Ana Bilgi Kartı */}
          <div className="stock-card" style={{ marginBottom: '2rem', background: 'linear-gradient(145deg, rgba(20,20,20,0.9), rgba(10,10,10,0.95))', border: '1px solid rgba(255,255,255,0.1)' }}>
              {/* Üst Bölüm: İsim ve Fiyat */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '25px' }}>
                  <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
                          <h1 style={{ fontSize: '3rem', margin: 0, lineHeight: 1, fontWeight: '900', color: 'var(--accent-color)' }}>{detail.symbol.replace('.IS', '')}</h1>
                      </div>
                      <h2 style={{ fontSize: '1.2rem', color: 'var(--text-secondary)', fontWeight: 'normal', margin: '12px 0' }}>{detail.name}</h2>
                       <div style={{ marginTop: '15px', display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
                           {detail.sector && <span className="badge" style={{ background: 'rgba(0, 200, 5, 0.1)', color: 'var(--accent-color)' }}>{detail.sector}</span>}
                           {detail.industry && <span className="badge" style={{ background: 'rgba(255, 255, 255, 0.05)', color: 'var(--text-secondary)' }}>{detail.industry}</span>}
                           {detail.index_code && detail.index_code !== '-' && (
                               <span className="badge" style={{ background: 'rgba(255, 215, 0, 0.1)', color: '#FFD700', fontWeight: 'bold' }}>
                                   #{detail.index_code}
                               </span>
                           )}
                       </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: '2.8rem', fontWeight: 'bold', letterSpacing: '-1px' }}>{detail.price?.toLocaleString()} ₺</div>
                      <div className={detail.change > 0 ? 'change-up' : 'change-down'} style={{ fontSize: '1.3rem', display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '8px', fontWeight: 'bold' }}>
                          <span>{detail.change > 0 ? '+' : ''}{detail.change?.toFixed(2)}</span>
                          <span style={{ fontSize: '1rem', opacity: 0.8 }}>({detail.changePercent?.toFixed(2)}%)</span>
                      </div>
                      <button 
                        onClick={(e) => toggleFavorite(detail.symbol, e)}
                        style={{ marginTop: '15px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: isFavorite ? '#FFD700' : 'var(--text-primary)', padding: '6px 20px', borderRadius: '20px', cursor:'pointer', fontSize: '0.85rem' }}
                      >
                         {isFavorite ? '★ Favorilerde' : '☆ Favoriye Ekle'}
                      </button>
                  </div>
              </div>

              <div style={{ height: '1px', background: 'linear-gradient(to right, rgba(255,255,255,0.1), transparent)', margin: '15px 0' }}></div>

              <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '3rem' }}>
                  {/* Şirket Künyesi */}
                  <div>
                      <h3 style={{ fontSize: '1rem', color: 'var(--text-secondary)', marginBottom: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          Şirket Hakkında
                          <span style={{ fontSize: '0.7rem', opacity: 0.6 }}>Kaynak: Yahoo Finance</span>
                      </h3>
                      <p style={{ 
                          lineHeight: '1.7', 
                          color: 'var(--text-primary)', 
                          fontSize: '1rem', 
                          opacity: 0.9,
                          display: '-webkit-box',
                          WebkitLineClamp: isDescExpanded ? 'unset' : 3,
                          WebkitBoxOrient: 'vertical',
                          overflow: 'hidden',
                          margin: 0
                      }}>
                          {detail.description}
                      </p>
                      <div style={{ display: 'flex', gap: '15px', alignItems: 'center', marginTop: '10px' }}>
                          {detail.description && detail.description.length > 200 && (
                              <button 
                                  onClick={() => setIsDescExpanded(!isDescExpanded)}
                                  style={{ 
                                      background: 'rgba(255,255,255,0.05)', 
                                      border: '1px solid rgba(255,255,255,0.1)', 
                                      color: 'var(--text-secondary)', 
                                      cursor: 'pointer', 
                                      padding: '4px 12px', 
                                      borderRadius: '6px',
                                      fontSize: '0.8rem'
                                  }}
                              >
                                  {isDescExpanded ? 'Kısalt' : 'Devamını oku'}
                              </button>
                          )}
                          {detail.website && (
                              <a href={detail.website} target="_blank" rel="noreferrer" style={{ color: 'var(--accent-color)', textDecoration: 'none', fontSize: '0.9rem', fontWeight: 'bold' }}>
                                  Resmi Web Sitesi →
                              </a>
                          )}
                      </div>
                  </div>

                  {/* Piyasa Verileri */}
                  <div>
                       <h3 style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '15px', display: 'flex', justifyContent: 'space-between' }}>
                           Piyasa Verileri
                           <span style={{ fontSize: '0.65rem' }}>Kaynak: Yahoo ({detail.last_updated ? new Date(detail.last_updated).toLocaleTimeString('tr-TR') : ''})</span>
                       </h3>
                       <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '15px' }}>
                           <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
                               <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>Piyasa Değeri</div>
                               <div style={{ fontSize: '1rem', fontWeight: 'bold' }}>{formatLargeNumber(detail.marketCap)}</div>
                           </div>
                           <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
                               <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>F/K Oranı</div>
                               <div style={{ fontSize: '1rem', fontWeight: 'bold' }}>{detail.peRatio && detail.peRatio !== '-' ? Number(detail.peRatio).toFixed(2) : '-'}</div>
                           </div>
                           <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
                               <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>PD/DD</div>
                               <div style={{ fontSize: '1rem', fontWeight: 'bold' }}>{detail.pd_dd && detail.pd_dd !== '-' ? Number(detail.pd_dd).toFixed(2) : '-'}</div>
                           </div>
                           <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
                               <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>FD/FAVÖK</div>
                               <div style={{ fontSize: '1rem', fontWeight: 'bold' }}>{detail.fd_favok && detail.fd_favok !== '-' ? Number(detail.fd_favok).toFixed(2) : '-'}</div>
                           </div>
                           <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
                               <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>Net Borç</div>
                               <div style={{ fontSize: '1rem', fontWeight: 'bold' }}>{formatLargeNumber(detail.netDebt)}</div>
                           </div>
                           <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
                               <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>Halka Açıklık</div>
                               <div style={{ fontSize: '1rem', fontWeight: 'bold' }}>{detail.floatShares && detail.sharesOutstanding ? ((detail.floatShares / detail.sharesOutstanding) * 100).toFixed(2) + '%' : '-'}</div>
                           </div>
                           <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)', gridColumn: 'span 2' }}>
                               <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>Sermaye (Ödenmiş)</div>
                               <div style={{ fontSize: '1rem', fontWeight: 'bold' }}>{formatLargeNumber(detail.sharesOutstanding)}</div>
                           </div>
                       </div>
                       {detail.calculation_source && (
                           <div style={{ marginTop: '15px', fontSize: '0.7rem', color: 'var(--text-secondary)', fontStyle: 'italic', background: 'rgba(255,255,255,0.02)', padding: '8px', borderRadius: '8px', borderLeft: '3px solid var(--accent-color)' }}>
                               ℹ️ {detail.calculation_source}
                               <br/>
                               <span style={{ fontSize: '0.65rem', opacity: 0.7 }}>
                                 Hesaplama Mantığı: Net Borç = (K.V. + U.V. Finansal Borçlar) - Nakit | PD/DD = Piyasa Değeri / Özkaynaklar | Rasyolar son bilançodaki finansal kalemler ve anlık fiyat üzerinden hesaplanmıştır.
                               </span>
                           </div>
                       )}
                  </div>
              </div>
          </div>
          </>
          )}

          {detailTab === 'Temel' && (
              <div className="fade-in">
          {/* Mali Tablolar Paneli */}
          <div className="stock-card" style={{ marginTop: '2rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '10px', marginBottom: '15px' }}>
                  <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '15px' }}>
                      Mali Tablolar (Son 12 Dönem)
                      <span style={{ fontSize: '0.7rem', color: 'var(--accent-color)', fontWeight: 'normal', border: '1px solid rgba(0, 200, 5, 0.2)', padding: '2px 8px', borderRadius: '4px', background: 'rgba(0, 200, 5, 0.05)' }}>
                          Kaynak: İş Yatırım {financials?.last_updated ? `(${new Date(financials.last_updated).toLocaleString('tr-TR')})` : ''}
                      </span>
                  </h3>
                  {finLoading && <span style={{ fontSize: '0.8rem', color: 'var(--accent-color)' }}>Veriler çekiliyor...</span>}
              </div>

              {financials ? (
                  <div className="stock-table-container" style={{ maxHeight: '600px', overflowY: 'auto' }}>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px', marginBottom: '15px', background: 'rgba(255,255,255,0.05)', padding: '10px', borderRadius: '8px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', justifyContent: 'space-between' }}>
                              <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Dönem 1:</label>
                              <select value={p1} onChange={(e) => setP1(e.target.value)} style={{ background: '#222', color: '#fff', border: '1px solid #444', padding: '4px 8px', borderRadius: '4px', fontSize: '0.8rem' }}>
                                  {financials.periods.map(p => <option key={p} value={p}>{p}</option>)}
                              </select>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', justifyContent: 'space-between' }}>
                              <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Dönem 2:</label>
                              <select value={p2} onChange={(e) => setP2(e.target.value)} style={{ background: '#222', color: '#fff', border: '1px solid #444', padding: '4px 8px', borderRadius: '4px', fontSize: '0.8rem' }}>
                                  {financials.periods.map(p => <option key={p} value={p}>{p}</option>)}
                              </select>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', justifyContent: 'space-between' }}>
                              <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Dönem 3:</label>
                              <select value={p3} onChange={(e) => setP3(e.target.value)} style={{ background: '#222', color: '#fff', border: '1px solid #444', padding: '4px 8px', borderRadius: '4px', fontSize: '0.8rem' }}>
                                  {financials.periods.map(p => <option key={p} value={p}>{p}</option>)}
                              </select>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', justifyContent: 'space-between' }}>
                              <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Dönem 4:</label>
                              <select value={p4} onChange={(e) => setP4(e.target.value)} style={{ background: '#222', color: '#fff', border: '1px solid #444', padding: '4px 8px', borderRadius: '4px', fontSize: '0.8rem' }}>
                                  {financials.periods.map(p => <option key={p} value={p}>{p}</option>)}
                              </select>
                          </div>
                      </div>

                      <table style={{ width: '100%' }}>
                          <thead style={{ position: 'sticky', top: 0, background: '#12161b', zIndex: 10, borderBottom: '2px solid rgba(255,255,255,0.1)' }}>
                              <tr>
                                  <th style={{ textAlign: 'left', width: '30%', fontSize: '0.75rem', padding: '12px 10px', color: 'var(--text-secondary)' }}>KALEM</th>
                                  <th style={{ textAlign: 'right', fontSize: '0.75rem', padding: '12px 10px', color: 'var(--accent-color)' }}>{p1}</th>
                                  <th style={{ textAlign: 'right', fontSize: '0.75rem', padding: '12px 10px', color: 'var(--accent-color)' }}>{p2}</th>
                                  <th style={{ textAlign: 'right', fontSize: '0.75rem', padding: '12px 10px', color: 'var(--accent-color)' }}>{p3}</th>
                                  <th style={{ textAlign: 'right', fontSize: '0.75rem', padding: '12px 10px', color: 'var(--accent-color)' }}>{p4}</th>
                              </tr>
                          </thead>
                          <tbody>
                               {financials.data.map(item => {
                                  const val1 = item.values[p1];
                                  const val2 = item.values[p2];
                                  const val3 = item.values[p3];
                                  const val4 = item.values[p4];

                                  return (
                                      <tr key={item.code} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                          <td style={{ fontSize: '0.8rem', padding: '12px 10px', fontWeight: '500' }}>{item.label}</td>
                                          <td style={{ textAlign: 'right', fontSize: '0.8rem', padding: '12px 10px' }}>
                                              { (val1 !== null && val1 !== undefined) ? Number(val1).toLocaleString() : '-' }
                                          </td>
                                          <td style={{ textAlign: 'right', fontSize: '0.8rem', padding: '12px 10px' }}>
                                              { (val2 !== null && val2 !== undefined) ? Number(val2).toLocaleString() : '-' }
                                          </td>
                                          <td style={{ textAlign: 'right', fontSize: '0.8rem', padding: '12px 10px' }}>
                                              { (val3 !== null && val3 !== undefined) ? Number(val3).toLocaleString() : '-' }
                                          </td>
                                          <td style={{ textAlign: 'right', fontSize: '0.8rem', padding: '12px 10px' }}>
                                              { (val4 !== null && val4 !== undefined) ? Number(val4).toLocaleString() : '-' }
                                          </td>
                                      </tr>
                                  );
                              })}
                          </tbody>
                      </table>
                  </div>
              ) : (
                  <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
                      {finLoading ? 'Yükleniyor...' : 'Mali veriler şu an ulaşılamaz durumda. Lütfen daha sonra tekrar deneyin.'}
                  </div>
              )}
          </div>
          </div>
          )}

          {detailTab === 'Değerleme' && (
              <div className="fade-in">
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                      {/* Graham Değerlemesi */}
                      <div className="stock-card">
                          <h3>Benjamin Graham Değerlemesi</h3>
                          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                              Graham'ın "Akıllı Yatırımcı" kitabındaki muhafazakar formül: <br/>
                              <strong>Fiyat = √ (22.5 * Hisse Başı Kar * Hisse Başı Özkaynak)</strong>
                          </p>
                          <div style={{ marginTop: '1.5rem', padding: '1rem', background: 'rgba(255,255,255,0.02)', borderRadius: '10px' }}>
                              {(() => {
                                  const netKar = detail.peRatio > 0 ? (detail.marketCap / detail.peRatio) : 0;
                                  const sermaye = detail.sharesOutstanding || 1;
                                  const ozkaynak = detail.marketCap / (detail.pd_dd || 1);
                                  
                                  const eps = netKar / sermaye;
                                  const bvps = ozkaynak / sermaye;
                                  const grahamPrice = Math.sqrt(22.5 * eps * bvps);
                                  const upside = ((grahamPrice / detail.price) - 1) * 100;

                                  return (
                                      <>
                                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                                              <span>Hisse Başı Kar (EPS):</span>
                                              <span style={{ fontWeight: 'bold' }}>{eps.toFixed(2)} ₺</span>
                                          </div>
                                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                                              <span>Defter Değeri (BVPS):</span>
                                              <span style={{ fontWeight: 'bold' }}>{bvps.toFixed(2)} ₺</span>
                                          </div>
                                          <div style={{ height: '1px', background: 'rgba(255,255,255,0.1)', margin: '15px 0' }}></div>
                                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                              <span style={{ fontSize: '1.1rem' }}>Graham Hedef Fiyat:</span>
                                              <span style={{ fontSize: '1.4rem', fontWeight: 'bold', color: 'var(--accent-color)' }}>{grahamPrice.toFixed(2)} ₺</span>
                                          </div>
                                          <div style={{ textAlign: 'right', marginTop: '5px', fontSize: '0.9rem', color: upside > 0 ? 'var(--gain-color)' : 'var(--loss-color)' }}>
                                              Potansiyel: {upside > 0 ? '+' : ''}{upside.toFixed(2)}%
                                          </div>
                                      </>
                                  );
                              })()}
                          </div>
                      </div>

                      {/* Çarpan Bazlı Değerleme */}
                      <div className="stock-card">
                          <h3>Çarpan Bazlı Hedef Fiyat</h3>
                          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>F/K ve PD/DD çarpanlarının sektör ortalamasına veya hedef değerine göre potansiyeli.</p>
                          <div style={{ marginTop: '1.5rem' }}>
                              {(() => {
                                  const currentFK = detail.peRatio || 0;
                                  const targetFK = 10; // Varsayılan muhafazakar hedef
                                  const eps = detail.peRatio > 0 ? (detail.price / detail.peRatio) : 0;
                                  const targetPrice = eps * targetFK;
                                  const upside = ((targetPrice / detail.price) - 1) * 100;

                                  return (
                                      <div style={{ padding: '1rem', background: 'rgba(255,255,255,0.02)', borderRadius: '10px' }}>
                                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                                              <span>Mevcut F/K:</span>
                                              <span style={{ fontWeight: 'bold' }}>{currentFK.toFixed(2)}</span>
                                          </div>
                                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                                              <span>Hedef F/K:</span>
                                              <span style={{ fontWeight: 'bold', color: 'var(--accent-color)' }}>{targetFK} (Örn.)</span>
                                          </div>
                                          <div style={{ height: '1px', background: 'rgba(255,255,255,0.1)', margin: '15px 0' }}></div>
                                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                              <span style={{ fontSize: '1.1rem' }}>F/K'ya Göre Eder:</span>
                                              <span style={{ fontSize: '1.4rem', fontWeight: 'bold', color: 'var(--accent-color)' }}>{targetPrice.toFixed(2)} ₺</span>
                                          </div>
                                          <div style={{ textAlign: 'right', marginTop: '5px', fontSize: '0.9rem', color: upside > 0 ? 'var(--gain-color)' : 'var(--loss-color)' }}>
                                              Potansiyel: {upside > 0 ? '+' : ''}{upside.toFixed(2)}%
                                          </div>
                                      </div>
                                  );
                              })()}
                          </div>
                      </div>

                      {/* Bedelsiz Potansiyeli */}
                      <div className="stock-card" style={{ gridColumn: 'span 2' }}>
                          <h3>Bedelsiz Sermaye Artırımı Potansiyeli</h3>
                          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Şirketin özkaynaklarının sermayeye oranı üzerinden hesaplanan teorik bedelsiz potansiyeli.</p>
                          {(() => {
                              const sermaye = detail.sharesOutstanding || 1;
                              const ozkaynak = detail.marketCap / (detail.pd_dd || 1);
                              const potansiyel = ((ozkaynak / sermaye) - 1) * 100;
                              
                              return (
                                  <div style={{ marginTop: '1.5rem', display: 'flex', alignItems: 'center', gap: '2rem' }}>
                                      <div style={{ flex: 1 }}>
                                          <div style={{ width: '100%', height: '12px', background: 'rgba(255,255,255,0.05)', borderRadius: '6px', overflow: 'hidden' }}>
                                              <div style={{ 
                                                  width: `${Math.min(potansiyel / 100, 100)}%`, 
                                                  height: '100%', 
                                                  background: 'linear-gradient(90deg, var(--accent-color), #00ff88)',
                                                  boxShadow: '0 0 10px var(--accent-color)'
                                              }}></div>
                                          </div>
                                      </div>
                                      <div style={{ fontSize: '1.8rem', fontWeight: 'bold', color: 'var(--accent-color)' }}>
                                          %{potansiyel.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                                      </div>
                                  </div>
                              );
                          })()}
                      </div>
                  </div>

                  <div style={{ marginTop: '2rem', padding: '2rem', background: 'rgba(0, 200, 5, 0.05)', borderRadius: '15px', border: '1px dashed var(--accent-color)', textAlign: 'center' }}>
                      <h4 style={{ color: 'var(--accent-color)', marginBottom: '10px' }}>💡 Bize Özel Formüller</h4>
                      <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                          Sizin için hazırladığımız özel değerleme modelleri ve analiz formülleri buraya eklenecektir. <br/>
                          Kullanmak istediğiniz özel bir formül varsa lütfen belirtin, hemen entegre edelim!
                      </p>
                  </div>
              </div>
          )}

          {detailTab === 'Teknik' && (
              <div className="fade-in">
                  <div className="stock-card" style={{ marginBottom: '1.5rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                          <h3 style={{ margin: 0 }}>Teknik Analiz Grafiği</h3>
                          <div className="tab-buttons" style={{ margin: 0 }}>
                              <button 
                                  className={chartMode === 'local' ? 'active' : ''} 
                                  onClick={() => setChartMode('local')}
                                  style={{ padding: '5px 15px', fontSize: '0.8rem' }}
                              >
                                  PhD Analiz
                              </button>
                              <button 
                                  className={chartMode === 'tv' ? 'active' : ''} 
                                  onClick={() => setChartMode('tv')}
                                  style={{ padding: '5px 15px', fontSize: '0.8rem' }}
                              >
                                  TradingView (Gelişmiş)
                              </button>
                          </div>
                      </div>

                      <div style={{ height: '500px', padding: chartMode === 'local' ? '10px' : 0, overflow: 'hidden' }}>
                          {chartMode === 'local' ? (
                              <PhDPriceChart data={stockHistory} />
                          ) : (
                              <TradingViewChart tvSymbol={detail?.tv_symbol} />
                          )}
                      </div>
                      
                      {chartMode === 'tv' && detail?.tv_symbol && (
                          <div style={{ marginTop: '10px', textAlign: 'right' }}>
                              <a 
                                href={`https://tr.tradingview.com/symbols/${detail.tv_symbol ? detail.tv_symbol.replace(':', '-') : ''}/`} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                style={{ fontSize: '0.8rem', color: 'var(--accent-color)', textDecoration: 'none' }}
                              >
                                ↗️ TradingView'de Tam Ekran Analiz Yap
                              </a>
                          </div>
                      )}
                  </div>
                  
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
                      {(() => {
                          const last = stockHistory[stockHistory.length - 1] || {};
                          return (
                              <>
                                  <div className="stock-card" style={{ textAlign: 'center' }}>
                                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>MA 20</div>
                                      <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: '#ff9800' }}>{last.MA20?.toFixed(2) || '-'} ₺</div>
                                  </div>
                                  <div className="stock-card" style={{ textAlign: 'center' }}>
                                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>MA 50</div>
                                      <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: '#2196f3' }}>{last.MA50?.toFixed(2) || '-'} ₺</div>
                                  </div>
                                  <div className="stock-card" style={{ textAlign: 'center' }}>
                                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>MA 200</div>
                                      <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: '#f44336' }}>{last.MA200?.toFixed(2) || '-'} ₺</div>
                                  </div>
                                  <div className="stock-card" style={{ textAlign: 'center' }}>
                                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>RSI (14)</div>
                                      <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: (last.RSI > 70 ? '#f44336' : last.RSI < 30 ? '#4caf50' : 'var(--accent-color)') }}>
                                          {last.RSI?.toFixed(2) || '-'}
                                      </div>
                                  </div>
                              </>
                          );
                      })()}
                  </div>
              </div>
          )}

          {detailTab === 'Takas' && (
              <div className="fade-in">
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                      {/* Alıcılar */}
                      <div className="stock-card">
                          <h3 style={{ borderBottom: '1px solid rgba(0, 200, 5, 0.2)', paddingBottom: '10px', color: 'var(--accent-color)' }}>En Çok Alanlar</h3>
                          <table style={{ width: '100%', marginTop: '10px' }}>
                              <thead>
                                  <tr style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                      <th style={{ textAlign: 'left' }}>Aracı Kurum</th>
                                      <th style={{ textAlign: 'right' }}>Lot</th>
                                      <th style={{ textAlign: 'right' }}>%</th>
                                  </tr>
                              </thead>
                              <tbody>
                                  {brokerageData?.top_buyers.map((b, i) => (
                                      <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                          <td style={{ padding: '8px 0', fontSize: '0.9rem' }}>{b.broker}</td>
                                          <td style={{ textAlign: 'right', fontWeight: 'bold' }}>{b.quantity.toLocaleString()}</td>
                                          <td style={{ textAlign: 'right' }}>
                                              <div style={{ display:'flex', alignItems:'center', justifyContent:'flex-end', gap:'5px' }}>
                                                  <div style={{ width: '40px', height:'4px', background:'rgba(255,255,255,0.1)', borderRadius:'2px' }}>
                                                      <div style={{ width: `${b.percentage}%`, height:'100%', background:'var(--accent-color)' }}></div>
                                                  </div>
                                                  %{b.percentage.toFixed(1)}
                                              </div>
                                          </td>
                                      </tr>
                                  ))}
                              </tbody>
                          </table>
                      </div>

                      {/* Satıcılar */}
                      <div className="stock-card">
                          <h3 style={{ borderBottom: '1px solid rgba(244, 67, 54, 0.2)', paddingBottom: '10px', color: '#f44336' }}>En Çok Satanlar</h3>
                          <table style={{ width: '100%', marginTop: '10px' }}>
                              <thead>
                                  <tr style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                      <th style={{ textAlign: 'left' }}>Aracı Kurum</th>
                                      <th style={{ textAlign: 'right' }}>Lot</th>
                                      <th style={{ textAlign: 'right' }}>%</th>
                                  </tr>
                              </thead>
                              <tbody>
                                  {brokerageData?.top_sellers.map((b, i) => (
                                      <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                          <td style={{ padding: '8px 0', fontSize: '0.9rem' }}>{b.broker}</td>
                                          <td style={{ textAlign: 'right', fontWeight: 'bold' }}>{Math.abs(b.quantity).toLocaleString()}</td>
                                          <td style={{ textAlign: 'right' }}>
                                              <div style={{ display:'flex', alignItems:'center', justifyContent:'flex-end', gap:'5px' }}>
                                                  <div style={{ width: '40px', height:'4px', background:'rgba(255,255,255,0.1)', borderRadius:'2px' }}>
                                                      <div style={{ width: `${b.percentage}%`, height:'100%', background:'#f44336' }}></div>
                                                  </div>
                                                  %{b.percentage.toFixed(1)}
                                              </div>
                                          </td>
                                      </tr>
                                  ))}
                              </tbody>
                          </table>
                      </div>
                  </div>

                  <div style={{ marginTop: '2rem', padding: '1.5rem', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '12px', textAlign: 'center' }}>
                      <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: 0 }}>
                         ℹ️ {brokerageData?.note} <br/>
                         Gerçek takas verileri günlük olarak takasbank üzerinden güncellenen BIST lisanslı veri yayıncılarından sağlanmalıdır.
                      </p>
                  </div>
              </div>
          )}
      </div>
  );
}

export default App;
