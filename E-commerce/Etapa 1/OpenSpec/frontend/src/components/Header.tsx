import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';
import { ShoppingCart, LogOut, User, Menu, X, ShoppingBag } from 'lucide-react';

export const Header: React.FC = () => {
  const { isAuthenticated, accountIdentifier, logout } = useAuth();
  const { cartCount } = useCart();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleSignOut = () => {
    logout();
    navigate('/');
    setMobileMenuOpen(false);
  };

  return (
    <header className="bg-white shadow-md sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          {/* Logo / Brand */}
          <Link
            to="/"
            className="flex items-center gap-2 text-indigo-600 font-bold text-xl hover:text-indigo-800 transition-colors"
            aria-label="Academic Store Landing Page"
          >
            <ShoppingBag className="h-6 w-6" />
            <span className="hidden sm:inline">Academic Store</span>
          </Link>

          {/* Desktop Navigation Controls */}
          <nav className="hidden md:flex items-center gap-6" aria-label="Desktop Main Navigation">
            <Link
              to="/"
              className="text-gray-600 hover:text-indigo-600 font-medium transition-colors"
              aria-label="Browse Product Catalog"
            >
              Catalog
            </Link>

            <Link
              to="/cart"
              className="relative p-2 text-gray-600 hover:text-indigo-600 transition-colors flex items-center"
              aria-label={`View Shopping Cart, contains ${cartCount} items`}
            >
              <ShoppingCart className="h-6 w-6" />
              {cartCount > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs font-bold rounded-full h-5 w-5 flex items-center justify-center animate-pulse">
                  {cartCount}
                </span>
              )}
            </Link>

            {/* Session Indicator & Auth state */}
            {isAuthenticated ? (
              <div className="flex items-center gap-4">
                <span className="text-sm text-gray-700 bg-indigo-50 border border-indigo-200 px-3 py-1 rounded-full flex items-center gap-1">
                  <User className="h-4 w-4 text-indigo-600" />
                  <span>Session: {accountIdentifier}</span>
                </span>
                <button
                  onClick={handleSignOut}
                  className="flex items-center gap-1 text-gray-600 hover:text-red-600 font-medium transition-colors cursor-pointer"
                  aria-label="Sign Out of session"
                >
                  <LogOut className="h-4 w-4" />
                  <span>Sign Out</span>
                </button>
              </div>
            ) : (
              <Link
                to="/login"
                className="bg-indigo-600 text-white px-4 py-2 rounded-md font-semibold hover:bg-indigo-700 transition-colors cursor-pointer"
                aria-label="Sign In or Register"
              >
                Sign In
              </Link>
            )}
          </nav>

          {/* Mobile Menu Button */}
          <div className="flex md:hidden items-center gap-4">
            <Link
              to="/cart"
              className="relative p-2 text-gray-600 hover:text-indigo-600 transition-colors flex items-center"
              aria-label={`View Shopping Cart, contains ${cartCount} items`}
            >
              <ShoppingCart className="h-6 w-6" />
              {cartCount > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs font-bold rounded-full h-5 w-5 flex items-center justify-center">
                  {cartCount}
                </span>
              )}
            </Link>

            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-md text-gray-600 hover:text-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              aria-expanded={mobileMenuOpen}
              aria-label="Toggle Navigation Menu"
            >
              {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-gray-100 bg-white" aria-label="Mobile Navigation Menu">
          <div className="px-2 pt-2 pb-4 space-y-1">
            <Link
              to="/"
              onClick={() => setMobileMenuOpen(false)}
              className="block px-3 py-2 rounded-md text-base font-medium text-gray-700 hover:bg-gray-50 hover:text-indigo-600"
              aria-label="Browse Product Catalog"
            >
              Catalog
            </Link>

            {isAuthenticated ? (
              <div className="pt-4 border-t border-gray-100 px-3">
                <div className="flex items-center gap-2 mb-3">
                  <User className="h-5 w-5 text-indigo-600" />
                  <span className="text-sm font-medium text-gray-700">Session: {accountIdentifier}</span>
                </div>
                <button
                  onClick={handleSignOut}
                  className="w-full text-left flex items-center gap-2 py-2 text-base font-medium text-red-600 hover:bg-red-50 rounded-md"
                  aria-label="Sign Out of session"
                >
                  <LogOut className="h-5 w-5" />
                  <span>Sign Out</span>
                </button>
              </div>
            ) : (
              <Link
                to="/login"
                onClick={() => setMobileMenuOpen(false)}
                className="block text-center mt-4 bg-indigo-600 text-white px-4 py-2 rounded-md font-semibold hover:bg-indigo-700 transition-colors"
                aria-label="Sign In or Register"
              >
                Sign In
              </Link>
            )}
          </div>
        </div>
      )}
    </header>
  );
};
