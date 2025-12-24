import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useTheme } from '../contexts/ThemeContext';

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
  showNotifications = true,
  showSearch = true,
  showMenu = true,
  onSearchPress,
  onNotificationPress,
  title,
}: HeaderProps) {
  const { theme, isDark, toggleTheme } = useTheme();

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
    logoIcon: {
      width: 8,
      height: 24,
      backgroundColor: theme.primary,
      borderRadius: 2,
      marginRight: 8,
    },
    appName: {
      fontSize: 22,
      fontWeight: '700',
      color: theme.text,
      letterSpacing: 0.5,
    },
    title: {
      fontSize: 20,
      fontWeight: '600',
      color: theme.text,
    },
    rightSection: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: 16,
    },
    iconButton: {
      padding: 4,
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
              <View style={styles.logoIcon} />
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
              onPress={() => router.push('/(worker)/profile')}
            >
              <Ionicons name="menu-outline" size={24} color={theme.text} />
            </TouchableOpacity>
          )}
        </View>
      </View>
    </View>
  );
}
