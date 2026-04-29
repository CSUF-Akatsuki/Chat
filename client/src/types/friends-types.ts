export interface FriendsProfile {
  id: string; // cognito_sub UUID
  username: string;
  friendship_status: string;
  friendship_created_at: string;
}

export interface FriendShipResponse {
  id: number;
  user_id: string;
  friend_id: string;
  created_at: Date;
}
