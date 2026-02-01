/**
 * Avatar Component - User avatar with multiple display options
 *
 * WCAG 2.1 AA Compliant:
 * - Proper alt text for images
 * - Semantic HTML
 * - Accessible status indicators
 */

import React, { useState, ImgHTMLAttributes } from 'react';

interface AvatarProps {
  /** Source URL for the image */
  src?: string;
  /** Alt text for the image */
  alt?: string;
  /** User initials fallback */
  initials?: string;
  /** Size of avatar */
  size?: 'small' | 'medium' | 'large' | 'xl';
  /** Background color for initials variant */
  bg?: string;
  /** Text color for initials */
  textColor?: string;
  /** Status indicator: online, offline, away */
  status?: 'online' | 'offline' | 'away' | 'none';
  /** Show status indicator */
  showStatus?: boolean;
  /** Optional class name */
  className?: string;
  /** Icon as fallback */
  icon?: React.ReactNode;
}

interface AvatarGroupProps {
  /** Array of avatar configurations */
  avatars: AvatarProps[];
  /** Maximum avatars to show before +X */
  maxVisible?: number;
  /** Size of avatars in group */
  size?: 'small' | 'medium' | 'large';
  /** Optional class name */
  className?: string;
}

const sizeMap = {
  small: {
    container: 32,
    text: 'text-xs',
    badge: 8,
  },
  medium: {
    container: 48,
    text: 'text-sm',
    badge: 10,
  },
  large: {
    container: 64,
    text: 'text-base',
    badge: 12,
  },
  xl: {
    container: 96,
    text: 'text-lg',
    badge: 16,
  },
};

const statusColors = {
  online: '#10b981',
  offline: '#6b7280',
  away: '#f59e0b',
  none: 'transparent',
};

/**
 * Avatar Component
 * Displays user avatar with image, initials, or icon fallback
 *
 * Usage:
 * ```tsx
 * <Avatar src="user.jpg" alt="John Doe" />
 * <Avatar initials="JD" status="online" />
 * <Avatar icon={<UserIcon />} />
 * ```
 */
export const Avatar: React.FC<AvatarProps> = ({
  src,
  alt = 'Avatar',
  initials,
  size = 'medium',
  bg = '#3b82f6',
  textColor = '#ffffff',
  status = 'none',
  showStatus = status !== 'none',
  className = '',
  icon,
}) => {
  const [imageError, setImageError] = useState(false);
  const sizeConfig = sizeMap[size];
  const dimension = sizeConfig.container;
  const badgeDimension = sizeConfig.badge;

  const handleImageError = () => {
    setImageError(true);
  };

  return (
    <div
      className={`relative inline-flex items-center justify-center ${className}`}
      style={{
        width: dimension,
        height: dimension,
      }}
    >
      {/* Image or Fallback */}
      {src && !imageError ? (
        <img
          src={src}
          alt={alt}
          className="w-full h-full rounded-full object-cover"
          onError={handleImageError}
        />
      ) : (
        <div
          className={`w-full h-full rounded-full flex items-center justify-center ${sizeConfig.text} font-semibold`}
          style={{
            backgroundColor: bg,
            color: textColor,
          }}
        >
          {icon || initials || '?'}
        </div>
      )}

      {/* Status Badge */}
      {showStatus && (
        <div
          className="absolute bottom-0 right-0 rounded-full border-2 border-white"
          style={{
            width: badgeDimension,
            height: badgeDimension,
            backgroundColor: statusColors[status],
          }}
          aria-label={`Status: ${status}`}
          role="img"
        />
      )}
    </div>
  );
};

/**
 * AvatarGroup Component
 * Displays multiple avatars in a stacked/grouped layout
 *
 * Usage:
 * ```tsx
 * <AvatarGroup
 *   avatars={[
 *     { src: 'user1.jpg', alt: 'User 1' },
 *     { initials: 'JD' },
 *   ]}
 *   maxVisible={3}
 * />
 * ```
 */
export const AvatarGroup: React.FC<AvatarGroupProps> = ({
  avatars,
  maxVisible = 3,
  size = 'medium',
  className = '',
}) => {
  const visible = avatars.slice(0, maxVisible);
  const hidden = avatars.length - maxVisible;

  const sizeConfig = sizeMap[size];
  const dimension = sizeConfig.container;
  const overlapOffset = dimension / 3;

  return (
    <div
      className={`flex items-center ${className}`}
      style={{
        marginRight: hidden > 0 ? dimension / 2 : 0,
      }}
    >
      {visible.map((avatar, index) => (
        <div
          key={index}
          style={{
            marginLeft: index === 0 ? 0 : `-${overlapOffset}px`,
            zIndex: visible.length - index,
          }}
        >
          <Avatar {...avatar} size={size} />
        </div>
      ))}

      {hidden > 0 && (
        <div
          className="flex items-center justify-center rounded-full border-2 border-gray-200 bg-gray-100 ml-2 font-semibold text-sm text-gray-600"
          style={{
            width: dimension,
            height: dimension,
          }}
          role="img"
          aria-label={`Plus ${hidden} more`}
        >
          +{hidden}
        </div>
      )}
    </div>
  );
};

/**
 * AvatarWithBadge Component
 * Avatar with badge/notification overlay
 */
export const AvatarWithBadge: React.FC<
  AvatarProps & { badgeContent?: React.ReactNode }
> = ({ badgeContent, ...avatarProps }) => {
  const sizeConfig = sizeMap[avatarProps.size || 'medium'];
  const dimension = sizeConfig.container;

  return (
    <div className="relative inline-flex">
      <Avatar {...avatarProps} />
      {badgeContent && (
        <div
          className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full flex items-center justify-center text-xs font-bold"
          style={{
            minWidth: Math.max(24, dimension / 3),
            height: Math.max(24, dimension / 3),
          }}
        >
          {badgeContent}
        </div>
      )}
    </div>
  );
};

Avatar.displayName = 'Avatar';
AvatarGroup.displayName = 'AvatarGroup';
AvatarWithBadge.displayName = 'AvatarWithBadge';

export { AvatarGroup, AvatarWithBadge };

export default Avatar;
