/**
 * Browser only: react-native-web's Alert.alert does nothing, so in the web
 * preview every "Are you sure?" (hire, end contract, close job) and every error
 * message silently disappeared. Map it to the browser's own dialogs.
 * Phones never run this - native Alert is untouched.
 */
import { Alert, AlertButton, Platform } from 'react-native';

if (Platform.OS === 'web' && typeof window !== 'undefined') {
  Alert.alert = (title: string, message?: string, buttons?: AlertButton[]) => {
    const text = [title, message].filter(Boolean).join('\n\n');
    const list = buttons && buttons.length ? buttons : [{ text: 'OK' }];
    const cancel = list.find(b => b.style === 'cancel');
    const actions = list.filter(b => b !== cancel);
    if (actions.length <= 1 && !cancel) {
      window.alert(text);
      actions[0]?.onPress?.();
      return;
    }
    // "Cancel" + one action -> OK/Cancel. More actions -> the first non-cancel one on OK.
    const action = actions.find(b => b.style === 'destructive') ?? actions[0];
    if (window.confirm(action?.text ? `${text}\n\n→ ${action.text}?` : text)) {
      action?.onPress?.();
    } else {
      cancel?.onPress?.();
    }
  };
}
