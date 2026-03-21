import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Platform, Modal, Pressable, Image } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import { useTranslation } from 'react-i18next';

interface HeaderProps {
  showBack?: boolean;
  showNotifications?: boolean;
  showSearch?: boolean;
  showMenu?: boolean;
  onSearchPress?: () => void;
  onNotificationPress?: () => void;
  title?: string;
}

export default function Header({
  showBack = false,
  showNotifications = false,
  showSearch = false,
  showMenu = true,
  onSearchPress,
  onNotificationPress,
  title,
}: HeaderProps) {
  const { theme, isDark, toggleTheme } = useTheme();
  const { logout } = useAuth();
  const { t } = useTranslation();
  const [showMenuModal, setShowMenuModal] = useState(false);

  const handleMenuPress = () => {
    setShowMenuModal(true);
  };

  const handleProfilePress = () => {
    setShowMenuModal(false);
    router.push('/(worker)/profile');
  };

  const handleSettingsPress = () => {
    setShowMenuModal(false);
    // Add settings navigation when implemented
  };

  const handleLogoutPress = async () => {
    setShowMenuModal(false);
    await logout();
  };

  const styles = StyleSheet.create({
    container: {
      backgroundColor: theme.surface,
      paddingTop: Platform.OS === 'ios' ? 50 : 40,
      paddingBottom: 12,
      paddingHorizontal: 16,
      borderBottomWidth: 1,
      borderBottomColor: theme.border,
      elevation: 4,
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.1,
      shadowRadius: 3,
    },
    content: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
    },
    leftSection: {
      flexDirection: 'row',
      alignItems: 'center',
      flex: 1,
    },
    backButton: {
      marginRight: 12,
    },
    logoContainer: {
      flexDirection: 'row',
      alignItems: 'center',
    },
    logoImage: {
      width: 36,
      height: 36,
      borderRadius: 18,
      backgroundColor: '#FFFFFF',
      padding: 1,
      marginRight: 6,
    },
    appName: {
      fontSize: 16,
      fontFamily: theme.fontBold,
      color: theme.text,
      letterSpacing: 0.5,
      flexShrink: 1,
    },
    title: {
      fontSize: 20,
      fontFamily: theme.fontSemiBold,
      color: theme.text,
    },
    rightSection: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: 8,
    },
    iconButton: {
      padding: 2,
    },
    modalOverlay: {
      flex: 1,
      backgroundColor: 'transparent',
    },
    menuModal: {
      position: 'absolute',
      top: Platform.OS === 'ios' ? 54 : 44,
      right: 8,
      backgroundColor: theme.surface,
      borderRadius: 8,
      paddingVertical: 8,
      minWidth: 160,
      elevation: 8,
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 4 },
      shadowOpacity: 0.2,
      shadowRadius: 8,
    },
    menuItem: {
      flexDirection: 'row',
      alignItems: 'center',
      paddingVertical: 14,
      paddingHorizontal: 16,
      gap: 12,
    },
    menuItemText: {
      fontSize: 14,
      fontFamily: 'Poppins_400Regular',
      color: theme.text,
    },
    menuItemLogout: {
      borderTopWidth: 1,
      borderTopColor: theme.border,
      marginTop: 8,
      paddingTop: 14,
    },
    menuItemLogoutText: {
      fontSize: 14,
      fontFamily: 'Poppins_500Medium',
      color: '#EF4444',
    },
  });

  return (
    <View style={styles.container}>
      <View style={styles.content}>
        {/* Left Section */}
        <View style={styles.leftSection}>
          {showBack && (
            <TouchableOpacity
              style={styles.backButton}
              onPress={() => router.back()}
            >
              <Ionicons name="arrow-back" size={24} color={theme.text} />
            </TouchableOpacity>
          )}
          
          {!title && (
            <View style={styles.logoContainer}>
              <Image 
                source={require('@/assets/images/logo.png')} 
                style={styles.logoImage}
                resizeMode="cover"
              />
              <Text style={styles.appName}>WORKER CONNECT</Text>
            </View>
          )}
          
          {title && (
            <Text style={styles.title}>{title}</Text>
          )}
        </View>

        {/* Right Section */}
        <View style={styles.rightSection}>
          {showNotifications && (
            <TouchableOpacity
              style={styles.iconButton}
              onPress={onNotificationPress}
            >
              <Ionicons name="notifications-outline" size={24} color={theme.text} />
            </TouchableOpacity>
          )}
          
          {showSearch && (
            <TouchableOpacity
              style={styles.iconButton}
              onPress={onSearchPress}
            >
              <Ionicons name="search-outline" size={24} color={theme.text} />
            </TouchableOpacity>
          )}
          
          <TouchableOpacity
            style={styles.iconButton}
            onPress={toggleTheme}
          >
            <Ionicons 
              name={isDark ? "sunny-outline" : "moon-outline"} 
              size={24} 
              color={theme.text} 
            />
          </TouchableOpacity>
          
          {showMenu && (
            <TouchableOpacity
              style={styles.iconButton}
              onPress={handleMenuPress}
            >
              <Ionicons name="menu-outline" size={24} color={theme.text} />
            </TouchableOpacity>
          )}
        </View>
      </View>

      {/* Menu Modal */}
      <Modal
        visible={showMenuModal}
        transparent
        animationType="fade"
        onRequestClose={() => setShowMenuModal(false)}
      >
        <Pressable 
          style={styles.modalOverlay} 
          onPress={() => setShowMenuModal(false)}
        >
          <View style={styles.menuModal}>
            <TouchableOpacity 
              style={styles.menuItem}
              onPress={handleProfilePress}
            >
              <Ionicons name="person-outline" size={20} color={theme.text} />
              <Text style={styles.menuItemText}>{t('nav.profile')}</Text>
            </TouchableOpacity>

            <TouchableOpacity 
              style={styles.menuItem}
              onPress={handleSettingsPress}
            >
              <Ionicons name="settings-outline" size={20} color={theme.text} />
              <Text style={styles.menuItemText}>{t('nav.settings')}</Text>
            </TouchableOpacity>

            <TouchableOpacity 
              style={[styles.menuItem, styles.menuItemLogout]}
              onPress={handleLogoutPress}
            >
              <Ionicons name="log-out-outline" size={20} color="#EF4444" />
              <Text style={styles.menuItemLogoutText}>{t('nav.logout')}</Text>
            </TouchableOpacity>
          </View>
        </Pressable>
      </Modal>
    </View>
  );
}
